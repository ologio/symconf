from pathlib import Path

from symconf import ConfigManager

config_dir = Path(__file__, "..", "test-config-dir/").resolve()
cm = ConfigManager(config_dir)


def test_matching_configs_exact() -> None:
    """
    Test matching exact style and scheme. Given strict mode not set (allowing
    relaxation to "none"), the order of matching should be

    1. (none, none)    :: none-none.aaa
    2. (none, scheme)  :: none-light.aaa
    3. (style, none)   :: test-none.aaa
    4. (style, scheme) :: test-light.ccc

    Yielding "test-light.aaa", "test-light.ccc" (unique only on config
    pathname).
    """
    any_light = cm.get_matching_configs(
        "test",
        style="test",
        scheme="light",
    )
    print(any_light)

    assert len(any_light) == 2
    assert any_light["aaa"].pathname == "test-none.aaa"
    assert any_light["ccc"].pathname == "test-light.ccc"


def test_matching_configs_any_style() -> None:
    """
    Test matching "any" style and exact scheme. Given strict mode not set
    (allowing relaxation to "none"), the order of matching should be

    1. (style, none)   :: none-none.aaa, test-none.aaa
    2. (none, none)    :: none-none.aaa
    3. (style, scheme) :: test-dark.bbb
    4. (none, scheme)  :: (nothing)

    Yielding "none-none.aaa" (should always overwrite "test-none.aaa" due to
    "any"'s preference for non-specific matches, i.e., "none"s),
    "test-none.ddd", "test-dark.bbb" (unique only on config pathname).
    """
    any_dark = cm.get_matching_configs(
        "test",
        style="any",
        scheme="dark",
    )

    assert len(any_dark) == 2
    assert any_dark["aaa"].pathname == "none-none.aaa"
    assert any_dark["bbb"].pathname == "test-dark.bbb"


def test_matching_configs_any_scheme() -> None:
    """
    Test matching exact style and "any" scheme. Given strict mode not set
    (allowing relaxation to "none"), the order of matching should be

    1. (none, scheme)  :: none-light.aaa & none-none.aaa
    2. (none, none)    :: none-none.aaa
    3. (style, scheme) :: test-dark.bbb & test-light.ccc & test-none.aaa
    4. (style, none)   :: test-none.aaa

    Yielding "test-none.aaa", "test-light.ccc", "test-dark.bbb"
    """
    test_any = cm.get_matching_configs(
        "test",
        style="test",
        scheme="any",
    )

    assert len(test_any) == 3
    assert test_any["aaa"].pathname == "test-none.aaa"
    assert test_any["bbb"].pathname == "test-dark.bbb"
    assert test_any["ccc"].pathname == "test-light.ccc"


def test_matching_scripts() -> None:
    """
    Test matching exact style and scheme. Given strict mode not set (allowing
    relaxation to "none"), the order of matching should be

    1. (none, none)    :: none-none.sh
    2. (none, scheme)  :: none-light.sh
    3. (style, none)   :: test-none.sh
    4. (style, scheme) :: (nothing)

    Yielding (ordered by dec specificity) "test-none.sh" as primary match, then
    relaxation match "none-none.sh".
    """
    test_any = cm.get_matching_scripts(
        "test",
        style="test",
        scheme="any",
    )

    assert len(test_any) == 2
    assert [p.pathname for p in test_any] == [
        "test-none.sh",
        "none-none.sh",
    ]

    any_light = cm.get_matching_scripts(
        "test",
        style="any",
        scheme="light",
    )

    assert len(any_light) == 2
    assert [p.pathname for p in any_light] == [
        "none-light.sh",
        "none-none.sh",
    ]

    any_dark = cm.get_matching_scripts(
        "test",
        style="any",
        scheme="dark",
    )

    assert len(any_dark) == 2
    assert [p.pathname for p in any_dark] == [
        "test-none.sh",
        "none-none.sh",
    ]
