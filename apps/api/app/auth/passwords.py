import anyio.to_thread
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # argon2id with the library's current recommended parameters
# Verified against when the account does not exist, so timing does not reveal which emails exist.
_DUMMY_HASH = _hasher.hash("not-a-real-password")

MIN_LENGTH = 10
MAX_LENGTH = 128


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-ish time: always performs one argon2 verification."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# Argon2 is deliberately slow (tens of ms). Awaiting it in a worker thread keeps one login or
# register from stalling every other request on the event loop.
async def ahash_password(password: str) -> str:
    return await anyio.to_thread.run_sync(hash_password, password)


async def averify_password(password_hash: str | None, password: str) -> bool:
    return await anyio.to_thread.run_sync(verify_password, password_hash, password)
