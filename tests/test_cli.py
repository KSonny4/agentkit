"""Tests for CLI."""

from agentkit.cli import create_parser


def test_parser_task_command():
    parser = create_parser()
    args = parser.parse_args(["task", "do something"])
    assert args.command == "task"
    assert args.prompt == "do something"


def test_parser_task_write_flag():
    parser = create_parser()
    args = parser.parse_args(["task", "--write", "do something"])
    assert args.write is True


def test_parser_task_readonly_default():
    parser = create_parser()
    args = parser.parse_args(["task", "do something"])
    assert args.write is False


def test_parser_evaluate_command():
    parser = create_parser()
    args = parser.parse_args(["evaluate", "--profile", "trading"])
    assert args.command == "evaluate"
    assert args.profile == "trading"


def test_parser_default_profile():
    parser = create_parser()
    args = parser.parse_args(["task", "test"])
    assert args.profile == "playground"
