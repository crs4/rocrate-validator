# Copyright (c) 2024 CRS4
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
