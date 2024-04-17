class: Workflow
cwlVersion: v1.2.0-dev2
doc: 'Abstract CWL Automatically generated from the Galaxy workflow file: sort-and-change-case'
inputs:
  0_Input Dataset:
    format: data
    type: File
outputs: {}
steps:
  1_Sort:
    in:
      input: 0_Input Dataset
    out:
    - out_file1
    run:
      class: Operation
      id: sort1
      inputs:
        input:
          format: Any
          type: File
      outputs:
        out_file1:
          doc: input
          type: File
  2_Change Case:
    in:
      input: 1_Sort/out_file1
    out:
    - out_file1
    run:
      class: Operation
      id: ChangeCase
      inputs:
        input:
          format: Any
          type: File
      outputs:
        out_file1:
          doc: tabular
          type: File

