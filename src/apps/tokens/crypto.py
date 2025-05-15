import hashlib
import secrets
import typing

from django.contrib.auth.hashers import (
    BasePasswordHasher,
    check_password,
    make_password,
)
from django.utils.crypto import constant_time_compare, get_random_string


def generate_key_pair() -> tuple[str, str]:
    """Generate a raw key and its hash."""
    raw_key = secrets.token_urlsafe(32)
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, hashed_key


def concatenate(left: str, right: str) -> str:
    return "{}.{}".format(left, right)


def split(concatenated: str) -> typing.Tuple[str, str]:
    left, _, right = concatenated.partition(".")
    return left, right


class Sha512ApiKeyHasher(BasePasswordHasher):
    algorithm = "sha512"

    def salt(self) -> str:
        """No need for a salt on a high entropy key."""
        return ""

    def encode(self, password: str, salt: str) -> str:
        if salt != "":
            raise ValueError("salt is unnecessary for high entropy API tokens.")
        hash = hashlib.sha512(password.encode()).hexdigest()
        return "%s$$%s" % (self.algorithm, hash)

    def verify(self, password: str, encoded: str) -> bool:
        encoded_2 = self.encode(password, "")
        return constant_time_compare(encoded, encoded_2)


class KeyGenerator:
    preferred_hasher = Sha512ApiKeyHasher()

    def __init__(self, prefix_length: int = 8, secret_key_length: int = 32):
        self.prefix_length = prefix_length
        self.secret_key_length = secret_key_length

    def get_prefix(self) -> str:
        return get_random_string(self.prefix_length)

    def get_secret_key(self) -> str:
        return get_random_string(self.secret_key_length)

    def hash(self, value: str) -> str:
        return make_password(value, hasher=self.preferred_hasher)

    def generate(self) -> typing.Tuple[str, str, str]:
        prefix = self.get_prefix()
        secret_key = self.get_secret_key()
        key = concatenate(prefix, secret_key)
        hashed_key = self.hash(key)
        return key, prefix, hashed_key

    def verify(self, key: str, hashed_key: str) -> bool:
        if self.using_preferred_hasher(hashed_key):
            # New simpler hasher
            result = self.preferred_hasher.verify(key, hashed_key)
        else:
            # Slower password hashers from Django
            # If verified, these will be transparently updated to the preferred hasher
            result = check_password(key, hashed_key)

        return result

    def using_preferred_hasher(self, hashed_key: str) -> bool:
        return hashed_key.startswith(f"{self.preferred_hasher.algorithm}$$")
