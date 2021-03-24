"""A custom JSON encoder for corrections

Author: Izaak Neutelings (March 2021)
Description: Reduce number of lines in JSON by collapsing lists
Adapted from:
  https://stackoverflow.com/questions/13249415/how-to-implement-custom-indentation-when-pretty-printing-with-the-json-module
  https://stackoverflow.com/questions/16264515/json-dumps-custom-formatting
"""
import json
import math
from typing import Any

import pydantic


def write(data: str, fname: str, **kwargs: Any) -> None:
    """Help function to quickly write JSON file formatted by JSONEncoder."""
    with open(fname, "w") as fout:
        fout.write(dumps(data, **kwargs))


def dumps(
    data: Any,
    sort_keys: bool = True,
    indent: int = 2,
    maxlistlen: int = 25,
    maxdictlen: int = 2,
    breakbrackets: bool = False,
) -> str:
    """Help function to quickly dump dictionary formatted by JSONEncoder."""
    if isinstance(data, pydantic.BaseModel):
        return data.json(
            cls=JSONEncoder,
            exclude_unset=True,
            indent=indent,
            maxlistlen=maxlistlen,
            maxdictlen=maxdictlen,
            breakbrackets=breakbrackets,
        )
    return json.dumps(
        data,
        cls=JSONEncoder,
        sort_keys=sort_keys,
        indent=indent,
        maxlistlen=maxlistlen,
        maxdictlen=maxdictlen,
        breakbrackets=breakbrackets,
    )


class JSONEncoder(json.JSONEncoder):
    """
    Encoder to make correctionlib JSON more compact, but still readable:
    - keep list of primitives (int, float, str) on one line,
      or split over several if the length is longer than a given maxlen
    - do not break line for short dictionary if all values are primitive
    - do not break line after bracket for first key of dictionary,
      unless itself nested in dictionary
    """

    def __init__(self, *args: Any, **kwargs: Any):
        if kwargs.get("indent", None) is None:
            kwargs["indent"] = 2
        # maximum of primitive elements per list, before breaking lines
        self.maxlistlen = kwargs.pop("maxlistlen", 25)
        # maximum of primitive elements per dict, before breaking lines
        self.maxdictlen = kwargs.pop("maxdictlen", 25)
        # break after opening bracket
        self.breakbrackets = kwargs.pop("breakbrackets", False)
        super().__init__(*args, **kwargs)
        self._indent = 0  # current indent
        self.parent = type(None)  # type of parent for recursive use

    def encode(self, obj: Any) -> str:
        grandparent = self.parent
        self.parent = type(obj)
        if isinstance(obj, (list, tuple)):  # lists, tuples
            output = []
            if all(
                isinstance(x, (int, float, str)) for x in obj
            ):  # list of primitives only
                if len(obj) > self.maxlistlen:  # break long list into multiple lines
                    nlines = math.ceil(len(obj) / float(self.maxlistlen))
                    maxlen = int(len(obj) / nlines)
                    indent_str = " " * (self._indent + self.indent)
                    for i in range(0, nlines):
                        line = []
                        for item in obj[i * maxlen : (i + 1) * maxlen]:
                            line.append(json.dumps(item))
                        output.append(", ".join(line))
                    if (
                        grandparent == dict or self.breakbrackets  # type: ignore
                    ):  # break first line after opening bracket
                        retval = (
                            "[\n"
                            + indent_str
                            + (",\n" + indent_str).join(output)
                            + "\n"
                            + " " * self._indent
                            + "]"
                        )
                    else:  # do not break first line
                        retval = (
                            "["
                            + " " * (self.indent - 1)
                            + (",\n" + indent_str).join(output)
                            + "\n"
                            + " " * self._indent
                            + "]"
                        )
                else:  # write short list on one line
                    for item in obj:
                        output.append(json.dumps(item))
                    retval = "[ " + ", ".join(output) + " ]"
            else:  # list of lists, tuples, dictionaries
                self._indent += self.indent
                indent_str = " " * self._indent
                for item in obj:
                    output.append(indent_str + self.encode(item))
                self._indent -= self.indent
                indent_str = " " * self._indent
                retval = "[\n" + ",\n".join(output) + "\n" + indent_str + "]"
        elif isinstance(obj, dict):  # dictionaries
            output = []
            if len(obj) <= self.maxdictlen and all(
                isinstance(obj[k], (int, float, str)) for k in obj
            ):  # write short dict on one line
                retval = (
                    "{ "
                    + ", ".join(json.dumps(k) + ": " + self.encode(obj[k]) for k in obj)
                    + " }"
                )
            else:  # break long dict into multiple line
                self._indent += self.indent
                indent_str = " " * self._indent
                first = (
                    grandparent in (type(None), dict) and not self.breakbrackets
                )  # break after opening bracket
                for key, value in obj.items():
                    valstr = self.encode(value)
                    if (
                        first and "\n" not in valstr
                    ):  # no break between opening bracket and first key
                        row = " " * (self.indent - 1) + json.dumps(key) + ": " + valstr
                    else:  # break before key
                        row = "\n" + indent_str + json.dumps(key) + ": " + valstr
                    output.append(row)
                    first = False
                self._indent -= self.indent
                indent_str = " " * self._indent
                retval = "{" + ",".join(output) + "\n" + indent_str + "}"
        else:  # use default formatting
            retval = json.dumps(obj)
        self.parent = grandparent
        return retval
