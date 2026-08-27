from data_science_agent import Agent, Benchmark, Dataset, Reproduction
from data_science_agent.sdk import API_STABILITY


def test_sdk_stable_exports():
    assert API_STABILITY["Agent"] == "Stable"
    assert callable(Agent)
    assert callable(Benchmark)
    assert callable(Reproduction)
    a = Agent()
    assert a.version == "4.2.10"
    ds = Dataset.from_path("sales.csv")
    assert ds.dataset_id == "sales"


def test_sdk_profile_contract():
    from data_science_agent import Agent

    prof = Agent().profile("benchmarks/v2/datasets/sales.csv")
    assert "rows" in prof and "columns" in prof
    assert prof["rows"] == 500
