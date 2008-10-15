"""
I define the class of resources.
"""

from advene.model.core.element import PackageElement, RESOURCE
from advene.model.core.content import WithContentMixin

class Resource(PackageElement, WithContentMixin):

    ADVENE_TYPE = RESOURCE

    def __init__(self, owner, id):
        PackageElement.__init__(self, owner, id)