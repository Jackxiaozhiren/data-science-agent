def test_imports() -> None:
    import dsa_agent  # noqa: F401
    import dsa_api  # noqa: F401
    import dsa_datasets  # noqa: F401
    import dsa_llm  # noqa: F401

    assert dsa_api.__version__ == "0.1.0"
