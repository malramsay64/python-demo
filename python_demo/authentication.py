"""Manage the hashing and verification of passwords.

This is split into a separate module to maintain the visibility of the approach
to managing passwords along with providing a single location in which to
modify / update the approach to handling passwords within the database.

"""

from passlib.hash import argon2


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return argon2.hash(password)
