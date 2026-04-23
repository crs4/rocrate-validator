# Copyright (c) 2024-2026 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
``rocrate-validator cache`` subcommand: inspect, warm and reset the HTTP cache
used by the validator.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from rich.table import Table

from rocrate_validator.cli.commands.errors import handle_error
from rocrate_validator.cli.main import cli, click
from rocrate_validator.models import Profile
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.cache_warmup import (
    WarmUpResult, discover_cacheable_urls_from_profiles, warm_up_urls)
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.paths import (get_default_http_cache_path,
                                           get_profiles_path)

logger = logging.getLogger(__name__)


def _resolve_cache_path(cache_path: Optional[Path]) -> Path:
    """Return the effective cache path, creating the parent directory."""
    if cache_path is None:
        path = get_default_http_cache_path()
    else:
        path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _reset_requester(cache_path: Path, offline: bool = False) -> None:
    """Re-initialize the HttpRequester singleton with the given cache path."""
    HttpRequester.reset()
    HttpRequester.initialize_cache(
        cache_path=str(cache_path),
        cache_max_age=-1,
        offline=offline,
    )


@cli.group("cache")
@click.pass_context
def cache(ctx):
    """
    [magenta]rocrate-validator:[/magenta] Manage the HTTP cache
    """


@cache.command("info")
@click.option(
    "--cache-path",
    type=click.Path(),
    default=None,
    show_default=False,
    help="Path to the HTTP cache directory (defaults to the user cache dir)",
)
@click.pass_context
def cache_info(ctx, cache_path: Optional[Path] = None):
    """
    Display information about the HTTP cache.
    """
    console = ctx.obj['console']
    try:
        resolved = _resolve_cache_path(cache_path)
        _reset_requester(resolved)
        info = HttpRequester().cache_info()
        table = Table(title="HTTP Cache", show_lines=False)
        table.add_column("Property", style="bold")
        table.add_column("Value")
        table.add_row("Path", str(info.get("path") or resolved))
        table.add_row("Backend", str(info.get("backend") or "—"))
        table.add_row("Persistent", "yes" if info.get("permanent") else "no")
        table.add_row("Offline mode", "yes" if info.get("offline") else "no")
        table.add_row("Entries", str(info.get("entries", 0)))
        size = info.get("size_bytes", 0) or 0
        table.add_row("Size", _format_bytes(size))
        console.print(table)
    except Exception as e:
        handle_error(e, console)


@cache.command("reset")
@click.option(
    "--cache-path",
    type=click.Path(),
    default=None,
    show_default=False,
    help="Path to the HTTP cache directory (defaults to the user cache dir)",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Do not prompt for confirmation before removing cache entries",
)
@click.pass_context
def cache_reset(ctx, cache_path: Optional[Path] = None, yes: bool = False):
    """
    Remove every entry from the HTTP cache.
    """
    console = ctx.obj['console']
    interactive = ctx.obj.get('interactive', False)
    exit_code = 0
    try:
        resolved = _resolve_cache_path(cache_path)
        _reset_requester(resolved)
        info = HttpRequester().cache_info()
        entries = info.get("entries", 0)
        size = _format_bytes(info.get("size_bytes", 0) or 0)
        console.print(
            f"[bold]HTTP cache:[/bold] {info.get('path') or resolved} "
            f"([cyan]{entries}[/cyan] entries, {size})"
        )
        if entries == 0:
            console.print("[green]Cache is already empty.[/green]")
            return
        if not yes:
            if not interactive:
                console.print(
                    "[yellow]Use --yes to remove entries in non-interactive mode.[/yellow]"
                )
                exit_code = 1
            else:
                confirm = click.confirm(
                    f"Remove all {entries} cached entries?", default=False
                )
                if not confirm:
                    console.print("Aborted.")
                else:
                    HttpRequester().clear_cache()
                    console.print("[green]HTTP cache cleared.[/green]")
        else:
            HttpRequester().clear_cache()
            console.print("[green]HTTP cache cleared.[/green]")
    except Exception as e:
        handle_error(e, console)
        return
    if exit_code:
        ctx.exit(exit_code)


@cache.command("warm")
@click.option(
    "--cache-path",
    type=click.Path(),
    default=None,
    show_default=False,
    help="Path to the HTTP cache directory (defaults to the user cache dir)",
)
@click.option(
    "--profiles-path",
    type=click.Path(exists=True),
    default=None,
    show_default=False,
    help="Path containing the profile definitions",
)
@click.option(
    "--extra-profiles-path",
    type=click.Path(exists=True),
    default=None,
    show_default=False,
    help="Path containing additional user profile definitions",
)
@click.option(
    "-p",
    "--profile-identifier",
    multiple=True,
    type=click.STRING,
    default=None,
    show_default=False,
    metavar="Profile-ID",
    help="Identifier of a profile to warm (may be given multiple times)",
)
@click.option(
    "--all-profiles",
    is_flag=True,
    default=False,
    help="Warm cacheable URLs declared by every installed profile",
)
@click.option(
    "--crate",
    multiple=True,
    type=click.STRING,
    default=None,
    metavar="URI",
    help="URL of a remote RO-Crate to download and cache (may be given multiple times)",
)
@click.pass_context
def cache_warm(
    ctx,
    cache_path: Optional[Path] = None,
    profiles_path: Optional[Path] = None,
    extra_profiles_path: Optional[Path] = None,
    profile_identifier: Optional[List[str]] = None,
    all_profiles: bool = False,
    crate: Optional[List[str]] = None,
):
    """
    Pre-populate the HTTP cache with resources declared by profiles and with
    optional remote RO-Crate URLs.
    """
    console = ctx.obj['console']
    exit_with_failure = False
    try:
        resolved_cache = _resolve_cache_path(cache_path)
        _reset_requester(resolved_cache, offline=False)
        profiles_dir = Path(profiles_path) if profiles_path else get_profiles_path()
        extra_dir = Path(extra_profiles_path) if extra_profiles_path else None

        requested_ids = list(profile_identifier or [])
        urls: List[str] = []
        profile_scope: Optional[str] = None

        if all_profiles or requested_ids or not crate:
            Profile.load_profiles(
                profiles_path=profiles_dir,
                extra_profiles_path=extra_dir,
            )
            loaded_profiles = list(Profile.all())
            if requested_ids:
                selected = []
                missing = []
                for ident in requested_ids:
                    profile = Profile.get_by_identifier(ident)
                    if profile is None:
                        missing.append(ident)
                    else:
                        selected.append(profile)
                if missing:
                    console.print(
                        f"[yellow]Profile(s) not found and skipped:[/yellow] {', '.join(missing)}"
                    )
                profile_scope = f"profiles: {', '.join(p.identifier for p in selected)}"
                urls = discover_cacheable_urls_from_profiles(selected)
            else:
                profile_scope = "all installed profiles"
                urls = discover_cacheable_urls_from_profiles(loaded_profiles)

        results: List[WarmUpResult] = []
        if urls:
            console.print(
                f"[bold]Warming cache for {profile_scope}[/bold] "
                f"([cyan]{len(urls)}[/cyan] URL(s))..."
            )
            results.extend(warm_up_urls(urls))

        if crate:
            console.print(
                f"[bold]Fetching remote RO-Crates[/bold] ([cyan]{len(crate)}[/cyan] URL(s))..."
            )
            results.extend(_warm_remote_crates(list(crate)))

        if not results:
            console.print("[yellow]Nothing to warm up.[/yellow]")
            return

        table = Table(title="Warm-up results", show_lines=False)
        table.add_column("URL", overflow="fold")
        table.add_column("Status")
        table.add_column("Detail")
        ok = 0
        failed = 0
        for r in results:
            colour = {"ok": "green", "skipped": "cyan", "failed": "red"}.get(r.status, "white")
            table.add_row(r.url, f"[{colour}]{r.status}[/{colour}]", r.detail or "")
            if r.status == "ok":
                ok += 1
            elif r.status == "failed":
                failed += 1
        console.print(table)
        console.print(
            f"[bold]Summary:[/bold] {ok} cached, {failed} failed, "
            f"{len(results) - ok - failed} skipped"
        )
        exit_with_failure = failed > 0
    except Exception as e:
        handle_error(e, console)
        return
    if exit_with_failure:
        ctx.exit(1)


def _warm_remote_crates(urls: List[str]) -> List[WarmUpResult]:
    """
    Download each remote RO-Crate URL via ``HttpRequester.fetch_fresh``
    so that its response is stored in the cache.
    """
    requester = HttpRequester()
    results: List[WarmUpResult] = []
    for url in urls:
        try:
            response = requester.fetch_fresh(url, stream=True, allow_redirects=True)
            status = getattr(response, "status_code", None)
            if status is None:
                results.append(WarmUpResult(url=url, status="failed", detail="no status code"))
                continue
            if status >= 400:
                results.append(WarmUpResult(url=url, status="failed", detail=f"HTTP {status}"))
                continue
            # Consume the response body so that the cache backend stores it.
            with tempfile.TemporaryFile() as tmp:
                shutil.copyfileobj(response.raw, tmp)
            results.append(WarmUpResult(url=url, status="ok", detail=f"HTTP {status}"))
        except Exception as e:
            logger.debug("Remote crate warm-up failed for %s: %s", url, e)
            results.append(WarmUpResult(url=url, status="failed", detail=str(e)))
    return results


def _format_bytes(size: int) -> str:
    if size <= 0:
        return "0 B"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    idx = 0
    value = float(size)
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.2f} {units[idx]}"
