import sys
from django.template.context import BaseContext

# Python 3.14 compatibility fix for Django template Context.__copy__
def _base_context_copy(self):
    duplicate = object.__new__(self.__class__)
    duplicate.__dict__.update(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate

if sys.version_info >= (3, 14):
    BaseContext.__copy__ = _base_context_copy
