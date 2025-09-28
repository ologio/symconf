from pathlib import Path

from symconf import Template, TOMLTemplate


def test_template_fill() -> None:
    # test simple replacment
    assert (
        Template("f{{a}} - f{{b}}").fill(
            {
                "a": 1,
                "b": 2,
            }
        )
        == "1 - 2"
    )

    # test nested brackets (using default pattern)
    assert (
        Template("{{ f{{a}} - f{{b}} }}").fill(
            {
                "a": 1,
                "b": 2,
            }
        )
        == "{{ 1 - 2 }}"
    )

    # test tight nested brackets (requires greedy quantifier)
    assert (
        Template("{{f{{a}} - f{{b}}}}").fill(
            {
                "a": 1,
                "b": 2,
            }
        )
        == "{{1 - 2}}"
    )


def test_toml_template_fill() -> None:
    test_group_dir = Path(
        __file__, "..", "test-config-dir/groups/test/"
    ).resolve()

    stacked_dict = TOMLTemplate.stack_toml(test_group_dir.iterdir())

    assert stacked_dict == {"base": "aaa", "concrete": "zzz"}
