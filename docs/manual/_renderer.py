from typing import Optional, Union

from griffe import dataclasses as dc
from plum import dispatch
from quartodoc import MdRenderer


class Renderer(MdRenderer):
    style = 'odm'

    @dispatch
    def signature(
        self,
        el: Union[dc.Class, dc.Function],
        source: Optional[dc.Alias] = None
    ):
        # exclude package name from function signature
        # XXX: doesn't work to set this in __init__
        self.display_name = 'short'

        return super().signature(el)
