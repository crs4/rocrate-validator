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

import copy as _copy
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.table import Table

from rocrate_validator.cli.commands.errors import handle_error
from rocrate_validator.cli.main import cli, click
from rocrate_validator.constants import BYTES_PER_KIB, HTTP_STATUS_BAD_REQUEST
from rocrate_validator.models import Profile
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.cache_warmup import WarmUpResult, discover_cacheable_urls_from_profiles, warm_up_urls
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.paths import get_default_http_cache_path, get_profiles_path

logger = logging.getLogger(__name__)


def _resolve_cache_path(cache_path: Optional[Path]) -> Path:
    """Return the effective cache path, creating the parent directory."""
    path = get_default_http_cache_path() if cache_path is None else Path(cache_path)
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


@cache.command("list")
@click.option(
    "--cache-path",
    type=click.Path(),
    default=None,
    show_default=False,
    help="Path to the HTTP cache directory (defaults to the user cache dir)",
)
@click.option(
    "--url",
    "url_filter",
    type=click.STRING,
    default=None,
    metavar="SUBSTRING",
    help="Show only entries whose URL contains SUBSTRING (case-insensitive)",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["url", "size", "created"], case_sensitive=False),
    default="created",
    show_default=True,
    help="Field to sort entries by",
)
@click.option(
    "--order",
    "sort_order",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default=None,
    show_default=False,
    help="Sort direction (default: desc for size/created, asc for url)",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print entries as JSON (size in bytes, datetimes as ISO 8601)",
)
@click.pass_context
def cache_list(
    ctx,
    cache_path: Optional[Path] = None,
    url_filter: Optional[str] = None,
    sort_by: str = "created",
    sort_order: Optional[str] = None,
    as_json: bool = False,
):
    """
    List entries currently stored in the HTTP cache (alias: `ls`).
    """
    console = ctx.obj['console']
    try:
        resolved = _resolve_cache_path(cache_path)
        _reset_requester(resolved)
        entries = _collect_cache_entries(
            url_filter=url_filter,
            sort_by=sort_by.lower(),
            sort_order=sort_order.lower() if sort_order else None,
        )

        if as_json:
            click.echo(json.dumps([_entry_to_dict(e) for e in entries], indent=2))
            return

        if not entries:
            if url_filter:
                console.print(f"[yellow]No entries match URL filter:[/yellow] {url_filter}")
            else:
                console.print("[yellow]Cache is empty.[/yellow]")
            return

        table = Table(title=f"HTTP Cache entries ({len(entries)})", show_lines=False)
        table.add_column("URL", overflow="fold")
        table.add_column("Size", justify="right")
        table.add_column("Content-Type")
        table.add_column("Created")
        table.add_column("Expires")
        total = 0
        for e in entries:
            total += e["size"]
            table.add_row(
                e["url"],
                _format_bytes(e["size"]),
                e["content_type"] or "—",
                _format_dt(e["created_at"]),
                _format_expires(e["expires"], e["is_expired"]),
            )
        console.print(table)
        console.print(f"[bold]Total:[/bold] {len(entries)} entries, {_format_bytes(total)}")
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
@click.option(
    "-u",
    "--url",
    multiple=True,
    type=click.STRING,
    default=None,
    metavar="URL",
    help="Arbitrary URL to fetch and cache (may be given multiple times)",
)
@click.pass_context
def cache_warm(
    ctx,
    cache_path: Optional[Path] = None,
    profiles_path: Optional[Path] = None,
    extra_profiles_path: Optional[Path] = None,
    profile_identifier: Optional[list[str]] = None,
    all_profiles: bool = False,
    crate: Optional[list[str]] = None,
    url: Optional[list[str]] = None,
):
    """
    Pre-populate the HTTP cache with resources declared by profiles and with
    optional remote RO-Crate URLs.
    """
    console = ctx.obj['console']
    explicit_urls = list(url or [])
    invalid_urls = [u for u in explicit_urls if not u.lower().startswith(("http://", "https://"))]
    if invalid_urls:
        raise click.BadParameter(
            f"expected an http(s):// address; got: {', '.join(invalid_urls)}",
            param_hint="'--url' / '-u'",
        )

    exit_with_failure = False
    try:
        resolved_cache = _resolve_cache_path(cache_path)
        _reset_requester(resolved_cache, offline=False)
        profiles_dir = Path(profiles_path) if profiles_path else get_profiles_path()
        extra_dir = Path(extra_profiles_path) if extra_profiles_path else None

        requested_ids = list(profile_identifier or [])
        urls: list[str] = []
        profile_scope: Optional[str] = None

        # Only fall back to "warm all profiles" when the user gave no other
        # source (no -p, no --crate, no --url, no --all-profiles).
        any_explicit_source = bool(crate or explicit_urls or requested_ids or all_profiles)
        if all_profiles or requested_ids or not any_explicit_source:
            urls, profile_scope = _resolve_warmup_urls_from_profiles(
                console, profiles_dir, extra_dir, requested_ids
            )

        results: list[WarmUpResult] = []
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

        if explicit_urls:
            console.print(
                f"[bold]Fetching explicit URLs[/bold] ([cyan]{len(explicit_urls)}[/cyan] URL(s))..."
            )
            results.extend(warm_up_urls(explicit_urls))

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


def _resolve_warmup_urls_from_profiles(console, profiles_dir, extra_dir, requested_ids):
    Profile.load_profiles(
        profiles_path=profiles_dir,
        extra_profiles_path=extra_dir,
    )
    loaded_profiles = list(Profile.all())
    if requested_ids:
        selected = []
        missing: list[str] = []
        ambiguous_fallbacks: list[tuple[str, Profile, list[Profile]]] = []
        for ident in requested_ids:
            profile = Profile.get_by_identifier(ident)
            if profile is None:
                candidates = Profile.get_by_token(ident) or []
                if candidates:
                    profile = max(candidates, key=lambda p: p.version)
                    if len(candidates) > 1:
                        ambiguous_fallbacks.append((ident, profile, candidates))
            if profile is None:
                missing.append(ident)
            else:
                selected.append(profile)
        for requested, resolved, candidates in ambiguous_fallbacks:
            other_versions = sorted(
                p.identifier for p in candidates if p.identifier != resolved.identifier
            )
            console.print(
                f"[yellow]Note:[/yellow] '{requested}' matched multiple profiles; "
                f"using [cyan]{resolved.identifier}[/cyan] (highest version). "
                f"Pass the full identifier to pick a different one "
                f"(available: {', '.join(other_versions)})."
            )
        if missing:
            console.print(
                f"[yellow]Profile(s) not found and skipped:[/yellow] {', '.join(missing)}"
            )
        profile_scope = f"profiles: {', '.join(p.identifier for p in selected)}"
        urls = discover_cacheable_urls_from_profiles(selected)
    else:
        profile_scope = "all installed profiles"
        urls = discover_cacheable_urls_from_profiles(loaded_profiles)
    return urls, profile_scope


def _warm_remote_crates(urls: list[str]) -> list[WarmUpResult]:
    """
    Download each remote RO-Crate URL via ``HttpRequester.fetch_fresh``
    so that its response is stored in the cache.
    """
    requester = HttpRequester()
    results: list[WarmUpResult] = []
    for url in urls:
        try:
            response = requester.fetch_fresh(url, allow_redirects=True)
            status = getattr(response, "status_code", None)
            if status is None:
                results.append(WarmUpResult(url=url, status="failed", detail="no status code"))
                continue
            if status >= HTTP_STATUS_BAD_REQUEST:
                results.append(WarmUpResult(url=url, status="failed", detail=f"HTTP {status}"))
                continue
            # Touch the body so the cache backend stores the full response.
            _ = response.content
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
    while value >= BYTES_PER_KIB and idx < len(units) - 1:
        value /= BYTES_PER_KIB
        idx += 1
    return f"{value:.2f} {units[idx]}"


def _format_dt(value: Optional[datetime]) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M:%SZ") if value.tzinfo else value.strftime("%Y-%m-%d %H:%M:%S")


def _format_expires(value: Optional[datetime], is_expired: bool) -> str:
    if value is None:
        return "never"
    formatted = _format_dt(value)
    return f"[red]{formatted} (expired)[/red]" if is_expired else formatted


_DEFAULT_SORT_ORDER = {"url": "asc", "size": "desc", "created": "desc"}


def _collect_cache_entries(
    url_filter: Optional[str] = None,
    sort_by: str = "size",
    sort_order: Optional[str] = None,
) -> list[dict]:
    """
    Read every cached response and return a list of plain dicts. Filtering
    and sorting happen here so the CLI rendering paths (table / JSON) share
    the same data shape.

    ``sort_order`` is one of ``"asc"``/``"desc"`` or ``None`` to use the
    field's natural default (URLs sort ascending; size and timestamps sort
    descending so the largest/most recent come first).
    """
    cache = getattr(HttpRequester().session, "cache", None)
    if cache is None:
        return []
    needle = url_filter.lower() if url_filter else None
    entries: list[dict] = []
    responses = getattr(cache, "responses", None) or {}
    for key in list(responses):
        try:
            resp = responses[key]
        except Exception as exc:
            logger.debug("Skipping unreadable cache entry %s: %s", key, exc)
            continue
        url = getattr(resp, "url", "") or ""
        if needle and needle not in url.lower():
            continue
        entries.append({
            "key": key,
            "url": url,
            "status": getattr(resp, "status_code", None),
            "size": int(getattr(resp, "size", 0) or 0),
            "content_type": (getattr(resp, "headers", {}) or {}).get("Content-Type"),
            "created_at": getattr(resp, "created_at", None),
            "expires": getattr(resp, "expires", None),
            "is_expired": bool(getattr(resp, "is_expired", False)),
        })
    effective_order = sort_order or _DEFAULT_SORT_ORDER.get(sort_by, "desc")
    reverse = effective_order == "desc"
    if sort_by == "url":
        entries.sort(key=lambda e: e["url"].lower(), reverse=reverse)
    elif sort_by == "created":
        entries.sort(key=lambda e: e["created_at"] or datetime.min, reverse=reverse)
    else:  # "size"
        entries.sort(key=lambda e: e["size"], reverse=reverse)
    return entries


def _entry_to_dict(entry: dict) -> dict:
    """JSON-safe view of an entry produced by ``_collect_cache_entries``."""
    def _iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value is not None else None
    return {
        "url": entry["url"],
        "status": entry["status"],
        "size_bytes": entry["size"],
        "content_type": entry["content_type"],
        "created_at": _iso(entry["created_at"]),
        "expires": _iso(entry["expires"]),
        "is_expired": entry["is_expired"],
    }


# Shell-style alias: `cache ls` runs the same callback as `cache list`.
# A shallow copy gives the alias its own name and hides it from --help so
# the command appears only once in the listing.
_cache_ls_alias = _copy.copy(cache_list)
_cache_ls_alias.name = "ls"
_cache_ls_alias.hidden = True
cache.add_command(_cache_ls_alias)
