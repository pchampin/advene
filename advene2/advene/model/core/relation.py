"""
I define the class of relations.
"""

from advene import _RAISE
from advene.model.core.element \
  import PackageElement, ANNOTATION, RELATION
from advene.model.core.content import WithContentMixin

class Relation(PackageElement, WithContentMixin):
    """
    I expose the protocol of a basic collection, to give access to the members
    of a relation. I also try to efficiently cache the results I know.
    """

    # Caching is performed as follow:
    # __init__ retrieves the number of members, and builds self.__idrefs
    # and self.__cache, a list of id-refs and instances respectively.
    # Whenever an index is accessed, the member if retrieved from self.__cache.
    # If None, its id-ref is retrieved from self.__idrefs and the element is
    # retrieved from the package. If the id-ref is None, the id-ref is
    # retrieved from the backend.

    # The use of add_cleaning_operation is complicated here.
    # We could choose to have a single cleaning operation, performed once on
    # cleaning, completely rewriting the member list.
    # We have chosen to enqueue every atomic operation on the member list in
    # the cleaning operation pending list, and perform them all on cleaning,
    # which is more efficient that the previous solution if cleaning is 
    # performed often enough.
    #
    # A third solution would be to try to optimize the cleaning by not
    # executing atomic operations which will be cancelled by further
    # operations. For example:::
    #     r[1] = a1
    #     r[1] = a2
    # will execute backend.update_member twice, while only the second one
    # is actually useful. So...

    ADVENE_TYPE = RELATION

    def __init__(self, owner, id, mimetype, schema, url, _new=False):
        PackageElement.__init__(self, owner, id)
        self._set_content_mimetype(mimetype, _init=True)
        self._set_content_schema(schema, _init=True)
        self._set_content_url(url, _init=True)

        if _new:
            self._cache = []
            self._idrefs = []
        else:
            c = owner._backend.count_members(owner._id, self._id)
            self._cache = [None,] * c
            self._idrefs = [None,] * c

    def __len__(self):
        return len(self._cache)

    def __iter__(self):
        """Iter over the members of this relation.

        If the relation contains unreachable members, an exception will be
        raised at the time of yielding those members.

        See also `iter_members`.
        """
        return self.iter_members(False)

    def __getitem__(self, i):
        """Return member with index i, or raise an exception if the item is
        unreachable.

        See also `get_member`  and `get_member_idref`.
        """
        if isinstance(i, slice): return self._get_slice(i)
        else: return self.get_member(i, _RAISE)

    def __setitem__(self, i, a):
        if isinstance(i, slice): return self._set_slice(i, a)
        assert getattr(a, "ADVENE_TYPE", None) == ANNOTATION
        o = self._owner
        assert o._can_reference(a)
        idref = a.make_idref_in(o)
        self._idrefs[i] = idref
        self._cache[i] = a
        self.add_cleaning_operation(o._backend.update_member,
                                    o._id, self._id, idref, i)

    def __delitem__(self, i):
        if isinstance(i, slice): return self._del_slice(i)
        del self._idrefs[i] # also guarantees that is is a valid index
        del self._cache[i]
        o = self._owner
        self.add_cleaning_operation(o._backend.remove_member,
                                    o._id, self._id, i)

    def _get_slice(self, s):
        c = len(self._cache)
        return [ self.get_member(i, _RAISE) for i in range(c)[s] ]

    def _set_slice(self, s, annotations):
        c = len(self._cache)
        indices = range(c)[s]
        same_length = (len(annotations) == len(indices))
        if s.step is None and not same_length:
            self._del_slice(s)
            insertpoint = s.start or 0
            for a in annotations:
                self.insert(insertpoint, a)
                insertpoint += 1
        else:
            if not same_length:
                raise ValueError("attempt to assign sequence of size %s to "
                                 "extended slice of size %s"
                                 % (len(annotations), len(indices)))
            for i,j in enumerate(indices):
                self.__setitem__(j, annotations[i])
        
    def _del_slice(self,s):
        c = len(self._cache)
        indices = range(c)[s]
        indices.sort()
        for offset, i in enumerate(indices):
            del self[i-offset]

    def insert(self, i, a):
        assert getattr(a, "ADVENE_TYPE", None) == ANNOTATION
        o = self._owner
        assert o._can_reference(a)
        c = len(self._cache)
        if i > c : i = c
        if i < -c: i = 0
        if i < 0 : i += c 
        idref = a.make_idref_in(o)
        self._idrefs.insert(i,idref)
        self._cache.insert(i,a)
        self.add_cleaning_operation(o._backend.insert_member,
                                    o._id, self._id, idref, i, c)
        # NB: it is important to pass to the backend the length c computed
        # *before* inserting the member
        
    def append(self, a):
        assert getattr(a, "ADVENE_TYPE", None) == ANNOTATION
        o = self._owner
        assert o._can_reference(a)
        idref = a.make_idref_in(o)
        c = len(self._cache)
        self._idrefs.append(idref)
        self._cache.append(a)
        self.add_cleaning_operation(o._backend.insert_member,
                                    o._id, self._id, idref, -1, c)
        # NB: it is important to pass to the backend the length c computed
        # *before* appending the member

    def extend(self, annotations):
        for a in annotations:
            self.append(a)

    def iter_members(self, _idrefs=True):
        """Iter over the members of this relation.

        If the relation contains unreachable members, their id-ref will be
        yielded instead.

        See also `__iter__` and `iter_member_idrefs`.
        """
        # NB: internally, _idrefs can be passed False to force exceptions
        if _idrefs:
            default = None
        else:
            default = _RAISE
        for i,m in enumerate(self._cache):
            if m is None:
                m = self.get_member(i, default)
                if m is None: # only possible when _idrefs is true
                    m = self.get_member_idref(i)
            yield m

    def iter_member_idrefs(self):
        """Iter over the id-refs of the members of this relation.

        See also `iter_members`.
        """
        for i,m in enumerate(self._idrefs):
            if m is not None:
                yield m
            else:
                yield self.get_member(i, _RAISE)

    def get_member(self, i, default=None):
        """Return element with index i, or default if it can not be retrieved.

        The difference with self[i] is that, if the member is unreachable,
        None is returned (or whatever value is passed as ``default``).

        Note that if ``i`` is an invalid index, an IndexError will still be
        raised.

        See also `__getitem__`  and `get_member_idref`.
        """
        # NB: internally, default can be passed _RAISE to force exceptions
        assert isinstance(i, int)
        r = self._cache[i]
        if r is None:
            o = self._owner
            idref = self._idrefs[i]
            if idref is None:
                c = len(self._cache)
                i = xrange(c)[i] # check index and convert negative
                idref = self._idrefs[i] = \
                    o._backend.get_member(o._id, self._id, i)
            r = self._cache[i] = o.get_element(idref, default)
        return r

    def get_member_idref(self, i):
        """Return id-ref of the element with index i.

        See also `__getitem__`  and `get_member`.
        """
        assert isinstance(i, int)
        r = self._idrefs[i]
        if r is None:
            o = self._owner
            c = len(self._idrefs)
            i = xrange(c)[i] # check index and convert negative
            r = self._idrefs[i] = o._backend.get_member(o._id, self._id, i)
        return r

#
