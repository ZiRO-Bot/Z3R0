"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fluent.syntax.ast as FTL
from fluent.syntax import FluentParser


if TYPE_CHECKING:
    from fluent.syntax.ast import Resource


class FluentType:
    def __init__(self):
        raise NotImplementedError


class FluentIdentifier(FluentType):
    def __init__(self, name: str, **kwargs):
        self.name: str = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Identifier={self.name}"


class FluentMessage(FluentType):
    def __init__(self, id: FluentIdentifier, value, attributes: list, **kwargs):
        self.id = id
        self.value = value
        self.attributes = attributes


class FluentPattern(FluentType):
    def __init__(self, elements: list, **kwargs):
        self.elements: list[FluentElement] = elements


class FluentElement(FluentType):
    def __init__(self, value, **kwargs):
        self.value = value

    def __str__(self):
        return str(self.value)


class FluentTextElement(FluentElement):
    pass


class FluentResolver:
    @staticmethod
    def resolveMessage(_, **kwargs):
        return FluentMessage(**kwargs)

    @staticmethod
    def resolvePattern(node, elements, **kwargs):
        if len(elements) == 1:
            return FluentResolver.resolveTextElement(node, value=elements[0].value)  # TODO
        return FluentPattern(elements, **kwargs)

    @staticmethod
    def resolveTextElement(_, **kwargs):
        return FluentTextElement(**kwargs)

    @staticmethod
    def resolveIdentifier(_, **kwargs):
        return FluentIdentifier(**kwargs)


class FluentCompiler:
    def compile(self, node: Any):
        if isinstance(node, FTL.BaseNode):
            nodename = type(node).__name__
            if not hasattr(FluentResolver, f"resolve{nodename}"):
                return node

            kwargs: dict[str, Any] = vars(node).copy()
            newKwargs: dict[str, Any] = {}
            for k, v in kwargs.items():
                newKwargs[k] = self.compile(v)
            attr = getattr(FluentResolver, f"resolve{nodename}", None)
            if attr:
                return attr(node, **newKwargs)
        if isinstance(node, (tuple, list)):
            return [self.compile(i) for i in node]
        return node


class FluentProvider:
    def __init__(self):
        self.root = Path("src/main/locale")
        self.bundles: dict[str, Any] = {}
        self.compiler = FluentCompiler()

    def get(self, msgId: str, locale: str) -> FluentMessage:
        with Path(self.root, f"{locale}.ftl").open() as fp:
            bundle = FluentParser().parse(fp.read())
        if not self.bundles.get(locale):
            self.bundles[locale] = {}
            for item in bundle.body:
                compiled = self.compiler.compile(item)
                if isinstance(compiled, FluentMessage):
                    self.bundles[locale][str(compiled.id)] = compiled
        return self.bundles[locale][msgId]

    def translate(self, msgId: str, locale: str, args: dict[str, Any] | None = None):
        return self.get(msgId, locale)


print(FluentProvider().translate("test", "en_US").value)
