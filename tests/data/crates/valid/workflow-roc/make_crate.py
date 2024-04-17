"""\
(Re)generate the RO-Crate metadata. Requires
https://github.com/ResearchObject/ro-crate-py.
"""

from pathlib import Path

from rocrate.rocrate import ROCrate


THIS_DIR = Path(__file__).absolute().parent
WF = THIS_DIR / "sort-and-change-case.ga"
CWL_DESC_WF = THIS_DIR / "sort-and-change-case.cwl"
DIAGRAM = "blank.png"
README = "README.md"
WF_LICENSE = "https://spdx.org/licenses/MIT.html"
CRATE_LICENSE = "https://spdx.org/licenses/Apache-2.0.html"


def main():
    crate = ROCrate(gen_preview=False)
    crate.root_dataset["license"] = CRATE_LICENSE
    wf = crate.add_workflow(WF, main=True, lang="galaxy", gen_cwl=True, properties={
        "license": WF_LICENSE,
        "name": "sort-and-change-case",
        "description": "sort lines and change text to upper case",
    })
    cwl_desc_wf = crate.add_workflow(CWL_DESC_WF, main=False, lang="cwl", properties={
        "@type": ["File", "SoftwareSourceCode", "HowTo"],
    })
    wf["subjectOf"] = cwl_desc_wf
    diagram = crate.add_file(DIAGRAM, properties={
        "@type": ["File", "ImageObject"],
    })
    wf["image"] = diagram
    readme = crate.add_file(README, properties={
        "encodingFormat": "text/markdown",
    })
    readme["about"] = crate.root_dataset
    crate.metadata.write(THIS_DIR)


if __name__ == "__main__":
    main()
