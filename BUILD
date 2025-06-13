load("@rules_python//python:pip.bzl", "compile_pip_requirements")
load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")

package(default_visibility = ["//notion_updater:__subpackages__"])

compile_pip_requirements(
    name = "requirements",
    requirements_in = "requirements.txt",
    requirements_txt = "requirements_lock.txt",
)

py_library(
    name = "field_keys",
    srcs = ["field_keys.py"],
)

py_binary(
    name = "notion_updater",
    srcs = ["notion_updater.py"],
    deps = [
        ":field_keys",
        "@pypi//absl_py",
        "@pypi//notion_client",
        "@pypi//python_dateutil",
    ],
)

py_test(
    name = "notion_updater_test",
    srcs = ["notion_updater_test.py"],
    deps = [
        ":field_keys",
        ":notion_updater",
        "@pypi//notion_client",
        "@pypi//parameterized",
    ],
)
