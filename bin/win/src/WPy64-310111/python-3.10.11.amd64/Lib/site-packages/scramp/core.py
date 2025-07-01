import hashlib
import unicodedata
from enum import IntEnum, unique
from functools import wraps
from operator import attrgetter
from os import urandom
from stringprep import (
    in_table_a1,
    in_table_b1,
    in_table_c12,
    in_table_c21_c22,
    in_table_c3,
    in_table_c4,
    in_table_c5,
    in_table_c6,
    in_table_c7,
    in_table_c8,
    in_table_c9,
    in_table_d1,
    in_table_d2,
)
from uuid import uuid4

from asn1crypto.x509 import Certificate

from scramp.utils import b64dec, b64enc, h, hi, hmac, uenc, xor

# https://tools.ietf.org/html/rfc5802
# https://www.rfc-editor.org/rfc/rfc7677.txt


@unique
class ClientStage(IntEnum):
    get_client_first = 1
    set_server_first = 2
    get_client_final = 3
    set_server_final = 4


@unique
class ServerStage(IntEnum):
    set_client_first = 1
    get_server_first = 2
    set_client_final = 3
    get_server_final = 4


def _check_stage(Stages, current_stage, next_stage):
    if current_stage is None:
        if next_stage != 1:
            raise ScramException(f"The method {Stages(1).name} must be called first.")
    elif current_stage == 4:
        raise ScramException("The authentication sequence has already finished.")
    elif next_stage != current_stage + 1:
        raise ScramException(
            f"The next method to be called is "
            f"{Stages(current_stage + 1).name}, not this method."
        )


class ScramException(Exception):
    def __init__(self, message, server_error=None):
        super().__init__(message)
        self.server_error = server_error

    def __str__(self):
        s_str = "" if self.server_error is None else f" {self.server_error}"
        return super().__str__() + s_str


MECHANISMS = (
    "SCRAM-SHA-1",
    "SCRAM-SHA-1-PLUS",
    "SCRAM-SHA-256",
    "SCRAM-SHA-256-PLUS",
    "SCRAM-SHA-512",
    "SCRAM-SHA-512-PLUS",
    "SCRAM-SHA3-512",
    "SCRAM-SHA3-512-PLUS",
)


CHANNEL_TYPES = (
    "tls-server-end-point",
    "tls-unique",
    "tls-unique-for-telnet",
)


def make_channel_binding(name, ssl_socket):
    if name == "tls-unique":
        return (name, ssl_socket.get_channel_binding(name))
    elif name == "tls-server-end-point":
        cert_bin = ssl_socket.getpeercert(binary_form=True)
        cert = Certificate.load(cert_bin)

        # Find the hash algorithm to use according to
        # https://tools.ietf.org/html/rfc5929#section-4
        hash_algo = cert.hash_algo
        if hash_algo in ("md5", "sha1"):
            hash_algo = "sha256"

        try:
            hash_obj = hashlib.new(hash_algo)
        except ValueError as e:
            raise ScramException(
                f"Hash algorithm {hash_algo} not supported by hashlib. {e}"
            )
        hash_obj.update(cert_bin)
        return ("tls-server-end-point", hash_obj.digest())
    else:
        raise ScramException(f"Channel binding name {name} not recognized.")


class ScramMechanism:
    MECH_LOOKUP = {
        "SCRAM-SHA-1": (hashlib.sha1, False, 4096, 0),
        "SCRAM-SHA-1-PLUS": (hashlib.sha1, True, 4096, 1),
        "SCRAM-SHA-256": (hashlib.sha256, False, 4096, 2),
        "SCRAM-SHA-256-PLUS": (hashlib.sha256, True, 4096, 3),
        "SCRAM-SHA-512": (hashlib.sha512, False, 4096, 4),
        "SCRAM-SHA-512-PLUS": (hashlib.sha512, True, 4096, 5),
        "SCRAM-SHA3-512": (hashlib.sha3_512, False, 10000, 6),
        "SCRAM-SHA3-512-PLUS": (hashlib.sha3_512, True, 10000, 7),
    }

    def __init__(self, mechanism="SCRAM-SHA-256"):
        if mechanism not in MECHANISMS:
            raise ScramException(
                f"The mechanism name '{mechanism}' is not supported. The "
                f"supported mechanisms are {MECHANISMS}."
            )
        self.name = mechanism
        (
            self.hf,
            self.use_binding,
            self.iteration_count,
            self.strength,
        ) = self.MECH_LOOKUP[mechanism]

    def make_auth_info(self, password, iteration_count=None, salt=None):
        if iteration_count is None:
            iteration_count = self.iteration_count
        salt, stored_key, server_key = _make_auth_info(
            self.hf, password, iteration_count, salt=salt
        )
        return salt, stored_key, server_key, iteration_count

    def make_stored_server_keys(self, salted_password):
        _, stored_key, server_key = _c_key_stored_key_s_key(self.hf, salted_password)
        return stored_key, server_key

    def make_server(self, auth_fn, channel_binding=None, s_nonce=None):
        return ScramServer(
            self, auth_fn, channel_binding=channel_binding, s_nonce=s_nonce
        )


def _make_auth_info(hf, password, i, salt=None):
    if salt is None:
        salt = urandom(16)

    salted_password = _make_salted_password(hf, password, salt, i)
    _, stored_key, server_key = _c_key_stored_key_s_key(hf, salted_password)
    return salt, stored_key, server_key


def _validate_channel_binding(channel_binding):
    if channel_binding is None:
        return

    if not isinstance(channel_binding, tuple):
        raise ScramException(
            "The channel_binding parameter must either be None or a tuple."
        )

    if len(channel_binding) != 2:
        raise ScramException(
            "The channel_binding parameter must either be None or a tuple of "
            "two elements (type, data)."
        )

    channel_type, channel_data = channel_binding
    if channel_type not in CHANNEL_TYPES:
        raise ScramException(
            "The channel_binding parameter must either be None or a tuple "
            "with the first element a str specifying one of the channel "
            "types {CHANNEL_TYPES}."
        )

    if not isinstance(channel_data, bytes):
        raise ScramException(
            "The channel_binding parameter must either be None or a tuple "
            "with the second element a bytes object containing the bind data."
        )


class ScramClient:
    def __init__(
        self, mechanisms, username, password, channel_binding=None, c_nonce=None
    ):
        if not isinstance(mechanisms, (list, tuple)):
            raise ScramException(
                "The 'mechanisms' parameter must be a list or tuple of "
                "mechanism names."
            )

        _validate_channel_binding(channel_binding)

        mechs = [ScramMechanism(m) for m in mechanisms]
        mechs = [
            m
            for m in mechs
            if channel_binding is not None
            or (channel_binding is None and not m.use_binding)
        ]
        if len(mechs) == 0:
            raise Exception("There are no suitable mechanisms in the list.")

        mech = sorted(mechs, key=attrgetter("strength"))[-1]
        self.hf, self.use_binding = mech.hf, mech.use_binding
        self.mechanism_name = mech.name

        if self.use_binding:
            if channel_binding is None:
                raise ScramException(
                    "The channel_binding parameter can't be None if channel "
                    "binding is required."
                )
        else:
            if channel_binding is not None:
                raise ScramException(
                    "The channel_binding parameter must be None if channel "
                    "binding is not required."
                )

        self.c_nonce = _make_nonce() if c_nonce is None else c_nonce
        self.username = username
        self.password = password
        self.channel_binding = channel_binding
        self.stage = None

    def _set_stage(self, next_stage):
        _check_stage(ClientStage, self.stage, next_stage)
        self.stage = next_stage

    def get_client_first(self):
        self._set_stage(ClientStage.get_client_first)
        self.client_first_bare, client_first = _get_client_first(
            self.username, self.c_nonce, self.channel_binding
        )
        return client_first

    def set_server_first(self, message):
        self._set_stage(ClientStage.set_server_first)
        self.server_first = message
        self.auth_message, self.nonce, self.salt, self.iterations = _set_server_first(
            message, self.c_nonce, self.client_first_bare, self.channel_binding
        )

    def get_client_final(self):
        self._set_stage(ClientStage.get_client_final)
        self.server_signature, cfinal = _get_client_final(
            self.hf,
            self.password,
            self.salt,
            self.iterations,
            self.nonce,
            self.auth_message,
            self.channel_binding,
        )
        return cfinal

    def set_server_final(self, message):
        self._set_stage(ClientStage.set_server_final)
        _set_server_final(message, self.server_signature)


def set_error(f):
    @wraps(f)
    def wrapper(self, *args, **kwds):
        try:
            return f(self, *args, **kwds)
        except ScramException as e:
            if e.server_error is not None:
                self.error = e.server_error
                self.stage = ServerStage.set_client_final
            raise e

    return wrapper


class ScramServer:
    def __init__(self, mechanism, auth_fn, channel_binding=None, s_nonce=None):
        self.m = mechanism

        _validate_channel_binding(channel_binding)

        if mechanism.use_binding:
            if channel_binding is None:
                raise ScramException(
                    "The mechanism requires channel binding, and so "
                    "channel_binding can't be None."
                )
        else:
            if channel_binding is not None:
                raise ScramException(
                    "The mechanism does not support channel binding, and so "
                    "channel_binding must be None."
                )

        self.channel_binding = channel_binding

        self.s_nonce = _make_nonce() if s_nonce is None else s_nonce
        self.auth_fn = auth_fn
        self.stage = None
        self.server_signature = None
        self.error = None

    def _set_stage(self, next_stage):
        _check_stage(ServerStage, self.stage, next_stage)
        self.stage = next_stage

    @set_error
    def set_client_first(self, client_first):
        self._set_stage(ServerStage.set_client_first)
        self.nonce, self.user, self.client_first_bare = _set_client_first(
            client_first, self.s_nonce, self.channel_binding
        )
        salt, self.stored_key, self.server_key, self.i = self.auth_fn(self.user)
        self.salt = b64enc(salt)

    @set_error
    def get_server_first(self):
        self._set_stage(ServerStage.get_server_first)
        self.auth_message, server_first = _get_server_first(
            self.nonce, self.salt, self.i, self.client_first_bare, self.channel_binding
        )
        return server_first

    @set_error
    def set_client_final(self, client_final):
        self._set_stage(ServerStage.set_client_final)
        self.server_signature = _set_client_final(
            self.m.hf,
            client_final,
            self.s_nonce,
            self.stored_key,
            self.server_key,
            self.auth_message,
            self.channel_binding,
        )

    @set_error
    def get_server_final(self):
        self._set_stage(ServerStage.get_server_final)
        return _get_server_final(self.server_signature, self.error)


def _make_nonce():
    return str(uuid4()).replace("-", "")


def _make_auth_message(nonce, client_first_bare, server_first, cbind_data):
    cbind_input = b64enc(_make_cbind_input(cbind_data))
    msg = client_first_bare, server_first, "c=" + cbind_input, "r=" + nonce
    return ",".join(msg)


def _make_salted_password(hf, password, salt, iterations):
    return hi(hf, uenc(saslprep(password)), salt, iterations)


def _c_key_stored_key_s_key(hf, salted_password):
    client_key = hmac(hf, salted_password, b"Client Key")
    stored_key = h(hf, client_key)
    server_key = hmac(hf, salted_password, b"Server Key")

    return client_key, stored_key, server_key


def _check_client_key(hf, stored_key, auth_msg, proof):
    client_signature = hmac(hf, stored_key, auth_msg)
    client_key = xor(client_signature, b64dec(proof))
    key = h(hf, client_key)

    if key != stored_key:
        raise ScramException("The client keys don't match.", SERVER_ERROR_INVALID_PROOF)


def _make_gs2_header(channel_binding):
    if channel_binding is None:
        return "n,,"
    else:
        channel_type, _ = channel_binding
        return f"p={channel_type},,"


def _make_cbind_input(channel_binding):
    gs2_header = _make_gs2_header(channel_binding).encode("ascii")
    if channel_binding is None:
        return gs2_header
    else:
        _, cbind_data = channel_binding
        return gs2_header + cbind_data


def _parse_message(msg):
    return dict((e[0], e[2:]) for e in msg.split(",") if len(e) > 1)


def _get_client_first(username, c_nonce, channel_binding):
    try:
        u = saslprep(username)
    except ScramException as e:
        raise ScramException(e.args[0], SERVER_ERROR_INVALID_USERNAME_ENCODING)

    bare = ",".join((f"n={u}", f"r={c_nonce}"))
    gs2_header = _make_gs2_header(channel_binding)
    return bare, gs2_header + bare


def _set_client_first(client_first, s_nonce, channel_binding):
    first_comma = client_first.index(",")
    second_comma = client_first.index(",", first_comma + 1)
    gs2_header = client_first[:second_comma].split(",")
    gs2_cbind_flag = gs2_header[0]
    gs2_char = gs2_cbind_flag[0]

    if gs2_char == "y":
        if channel_binding is not None:
            raise ScramException(
                "Recieved GS2 flag 'y' which indicates that the client "
                "doesn't think the server supports channel binding, but in "
                "fact it does.",
                SERVER_ERROR_SERVER_DOES_SUPPORT_CHANNEL_BINDING,
            )

    elif gs2_char == "n":
        if channel_binding is not None:
            raise ScramException(
                "Received GS2 flag 'n' which indicates that the client "
                "doesn't require channel binding, but the server does.",
                SERVER_ERROR_SERVER_DOES_SUPPORT_CHANNEL_BINDING,
            )

    elif gs2_char == "p":
        if channel_binding is None:
            raise ScramException(
                "Received GS2 flag 'p' which indicates that the client "
                "requires channel binding, but the server does not.",
                SERVER_ERROR_CHANNEL_BINDING_NOT_SUPPORTED,
            )

        channel_type, _ = channel_binding
        cb_name = gs2_cbind_flag.split("=")[-1]
        if cb_name != channel_type:
            raise ScramException(
                f"Received channel binding name {cb_name} but this server "
                f"supports the channel binding name {channel_type}.",
                SERVER_ERROR_UNSUPPORTED_CHANNEL_BINDING_TYPE,
            )

    else:
        raise ScramException(
            f"Received GS2 flag {gs2_char} which isn't recognized.",
            SERVER_ERROR_OTHER_ERROR,
        )

    client_first_bare = client_first[second_comma + 1 :]
    msg = _parse_message(client_first_bare)
    c_nonce = msg["r"]
    nonce = c_nonce + s_nonce
    user = msg["n"]

    return nonce, user, client_first_bare


def _get_server_first(nonce, salt, iterations, client_first_bare, channel_binding):
    sfirst = ",".join((f"r={nonce}", f"s={salt}", f"i={iterations}"))
    auth_msg = _make_auth_message(nonce, client_first_bare, sfirst, channel_binding)
    return auth_msg, sfirst


def _set_server_first(server_first, c_nonce, client_first_bare, channel_binding):
    msg = _parse_message(server_first)
    if "e" in msg:
        raise ScramException(f"The server returned the error: {msg['e']}")
    nonce = msg["r"]
    salt = msg["s"]
    iterations = int(msg["i"])

    if not nonce.startswith(c_nonce):
        raise ScramException("Client nonce doesn't match.", SERVER_ERROR_OTHER_ERROR)

    auth_msg = _make_auth_message(
        nonce, client_first_bare, server_first, channel_binding
    )
    return auth_msg, nonce, salt, iterations


def _get_client_final(
    hf, password, salt_str, iterations, nonce, auth_msg_str, cbind_data
):
    salt = b64dec(salt_str)
    salted_password = _make_salted_password(hf, password, salt, iterations)
    client_key, stored_key, server_key = _c_key_stored_key_s_key(hf, salted_password)

    auth_msg = uenc(auth_msg_str)

    client_signature = hmac(hf, stored_key, auth_msg)
    client_proof = xor(client_key, client_signature)
    server_signature = hmac(hf, server_key, auth_msg)
    cbind_input = _make_cbind_input(cbind_data)
    msg = ["c=" + b64enc(cbind_input), "r=" + nonce, "p=" + b64enc(client_proof)]
    return b64enc(server_signature), ",".join(msg)


SERVER_ERROR_INVALID_ENCODING = "invalid-encoding"
SERVER_ERROR_EXTENSIONS_NOT_SUPPORTED = "extensions-not-supported"
SERVER_ERROR_INVALID_PROOF = "invalid-proof"
SERVER_ERROR_INVALID_ENCODING = "invalid-encoding"
SERVER_ERROR_CHANNEL_BINDINGS_DONT_MATCH = "channel-bindings-dont-match"
SERVER_ERROR_SERVER_DOES_SUPPORT_CHANNEL_BINDING = "server-does-support-channel-binding"
SERVER_ERROR_SERVER_DOES_NOT_SUPPORT_CHANNEL_BINDING = (
    "server does not support channel binding"
)
SERVER_ERROR_CHANNEL_BINDING_NOT_SUPPORTED = "channel-binding-not-supported"
SERVER_ERROR_UNSUPPORTED_CHANNEL_BINDING_TYPE = "unsupported-channel-binding-type"
SERVER_ERROR_UNKNOWN_USER = "unknown-user"
SERVER_ERROR_INVALID_USERNAME_ENCODING = "invalid-username-encoding"
SERVER_ERROR_NO_RESOURCES = "no-resources"
SERVER_ERROR_OTHER_ERROR = "other-error"


def _set_client_final(
    hf, client_final, s_nonce, stored_key, server_key, auth_msg_str, cbind_data
):
    auth_msg = uenc(auth_msg_str)

    msg = _parse_message(client_final)
    nonce = msg["r"]
    proof = msg["p"]
    channel_binding = msg["c"]
    if not b64dec(channel_binding) == _make_cbind_input(cbind_data):
        raise ScramException(
            "The channel bindings don't match.",
            SERVER_ERROR_CHANNEL_BINDINGS_DONT_MATCH,
        )

    if not nonce.endswith(s_nonce):
        raise ScramException("Server nonce doesn't match.", SERVER_ERROR_OTHER_ERROR)

    _check_client_key(hf, stored_key, auth_msg, proof)

    sig = hmac(hf, server_key, auth_msg)
    return b64enc(sig)


def _get_server_final(server_signature, error):
    return f"v={server_signature}" if error is None else f"e={error}"


def _set_server_final(message, server_signature):
    msg = _parse_message(message)
    if "e" in msg:
        raise ScramException(f"The server returned the error: {msg['e']}")

    if server_signature != msg["v"]:
        raise ScramException(
            "The server signature doesn't match.", SERVER_ERROR_OTHER_ERROR
        )


def saslprep(source):
    # mapping stage
    #   - map non-ascii spaces to U+0020 (stringprep C.1.2)
    #   - strip 'commonly mapped to nothing' chars (stringprep B.1)
    data = "".join(" " if in_table_c12(c) else c for c in source if not in_table_b1(c))

    # normalize to KC form
    data = unicodedata.normalize("NFKC", data)
    if not data:
        return ""

    # check for invalid bi-directional strings.
    # stringprep requires the following:
    #   - chars in C.8 must be prohibited.
    #   - if any R/AL chars in string:
    #       - no L chars allowed in string
    #       - first and last must be R/AL chars
    # this checks if start/end are R/AL chars. if so, prohibited loop
    # will forbid all L chars. if not, prohibited loop will forbid all
    # R/AL chars instead. in both cases, prohibited loop takes care of C.8.
    is_ral_char = in_table_d1
    if is_ral_char(data[0]):
        if not is_ral_char(data[-1]):
            raise ScramException(
                "malformed bidi sequence", SERVER_ERROR_INVALID_ENCODING
            )
        # forbid L chars within R/AL sequence.
        is_forbidden_bidi_char = in_table_d2
    else:
        # forbid R/AL chars if start not setup correctly; L chars allowed.
        is_forbidden_bidi_char = is_ral_char

    # check for prohibited output
    # stringprep tables A.1, B.1, C.1.2, C.2 - C.9
    for c in data:
        # check for chars mapping stage should have removed
        assert not in_table_b1(c), "failed to strip B.1 in mapping stage"
        assert not in_table_c12(c), "failed to replace C.1.2 in mapping stage"

        # check for forbidden chars
        for f, msg in (
            (in_table_a1, "unassigned code points forbidden"),
            (in_table_c21_c22, "control characters forbidden"),
            (in_table_c3, "private use characters forbidden"),
            (in_table_c4, "non-char code points forbidden"),
            (in_table_c5, "surrogate codes forbidden"),
            (in_table_c6, "non-plaintext chars forbidden"),
            (in_table_c7, "non-canonical chars forbidden"),
            (in_table_c8, "display-modifying/deprecated chars forbidden"),
            (in_table_c9, "tagged characters forbidden"),
            (is_forbidden_bidi_char, "forbidden bidi character"),
        ):
            if f(c):
                raise ScramException(msg, SERVER_ERROR_INVALID_ENCODING)

    return data
