"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Iterable

import discord
from discord.app_commands import Group as AppGroup
from discord.ext import commands
from discord.utils import MISSING


if TYPE_CHECKING:
    from discord.app_commands import locale_str as LocaleStr

    AutocompleteCallbackTypeReturn = Iterable[Any] | Awaitable[Iterable[Any]]
    AutocompleteCallbackType = Callable[..., AutocompleteCallbackTypeReturn] | Callable[..., AutocompleteCallbackTypeReturn]


@discord.utils.copy_doc(commands.Command)
class ZCommand(commands.Command):
    def __init__(
        self,
        func: Callable,
        /,
        # I use desc instead of description to avoid the content being casted as String
        desc: LocaleStr | str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(func, **kwargs)
        self.localeName: LocaleStr | None = kwargs.get("localeName")
        if not self.description and desc is not None:
            self.description: LocaleStr | str = desc or ""

    def autocomplete(self, name: str) -> Callable[[AutocompleteCallbackType], AutocompleteCallbackType]:
        def decorator(callback: AutocompleteCallbackType) -> AutocompleteCallbackType:
            # TODO: Outside of the scope of this PR
            return callback

        return decorator


@discord.utils.copy_doc(commands.HybridCommand)
class ZHybridCommand(commands.HybridCommand, ZCommand):
    __merge_group__: AppGroup | None = None

    def __init__(
        self,
        func: Callable,
        /,
        **kwargs: Any,
    ) -> None:
        mergeTo = kwargs.pop("mergeTo", None)
        super().__init__(func, **kwargs)
        self.__merge_group__ = mergeTo
        if self.localeName:
            self._locale_name = self.localeName


@discord.utils.copy_doc(commands.Group)
class ZGroup(commands.Group, ZCommand):
    def command(self, *args: Any, **kwargs: Any) -> Callable[..., ZCommand]:
        def wrapped(func) -> ZCommand:
            kwargs.setdefault("parent", self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapped

    def group(self, *args: Any, **kwargs: Any) -> Callable[..., ZGroup]:
        def wrapped(func) -> ZGroup:
            kwargs.setdefault("parent", self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapped


@discord.utils.copy_doc(commands.HybridGroup)
class ZHybridGroup(commands.HybridGroup, ZGroup):
    # TODO
    pass


def command(
    name: LocaleStr | str = MISSING,
    localeName: LocaleStr = MISSING,
    description: LocaleStr | str = MISSING,
    help: str = MISSING,
    aliases: Iterable[str] = MISSING,
    hybrid: bool = False,
    mergeTo: AppGroup = MISSING,
    **attrs: Any,
) -> Callable[..., ZCommand | ZHybridCommand]:
    """
    Custom @command decorator

    Should give me more control on the locale name
    """
    cls = ZHybridCommand if hybrid else ZCommand

    def decorator(func) -> ZCommand | ZHybridCommand:
        if isinstance(func, ZCommand | ZHybridCommand):
            raise TypeError("Function is already a command.")

        kwargs = {}
        kwargs.update(attrs)
        if name is not MISSING:
            kwargs["name"] = name
        if localeName is not MISSING:
            kwargs["localeName"] = localeName
        if description is not MISSING:
            kwargs["desc"] = description
        if help is not MISSING:
            kwargs["help"] = help
        if aliases is not MISSING:
            kwargs["aliases"] = aliases
        if mergeTo is not MISSING:
            kwargs["mergeTo"] = mergeTo

        return cls(func, **kwargs)

    return decorator


def group(
    name: LocaleStr | str = MISSING,
    localeName: LocaleStr = MISSING,
    description: LocaleStr | str = MISSING,
    help: str = MISSING,
    aliases: Iterable[str] = MISSING,
    hybrid: bool = False,
    **attrs: Any,
) -> Callable[..., ZGroup | ZHybridGroup]:
    """
    Custom @group decorator

    Should give me more control on the locale name
    """
    cls = ZHybridGroup if hybrid else ZGroup

    def decorator(func) -> ZGroup | ZHybridGroup:
        if isinstance(func, ZGroup | ZHybridGroup):
            raise TypeError("Function is already a command.")

        kwargs = {}
        kwargs.update(attrs)
        if name is not MISSING:
            kwargs["name"] = name
        if localeName is not MISSING:
            kwargs["localeName"] = localeName
        if description is not MISSING:
            kwargs["description"] = description
        if help is not MISSING:
            kwargs["help"] = help
        if aliases is not MISSING:
            kwargs["aliases"] = aliases

        return cls(func, **kwargs)

    return decorator
