import sys
import os
import requests
import json


def main():
    my_input = os.environ["INPUT_MYINPUT"]
    my_output = f"Testing: {my_input}"
    test(my_output)


if __name__ == "__main__":
    main()

def test(output):
  print(f"::set-output name=myOutput::{output}")