import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from src.backtest import forward_returns
from src.signals import Signal, offline_classifier, position
from src.llm import structured_call
from src.main import load_news

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2025-01-01T21:00:00Z", periods=24, freq="D")
        self.frame = pd.DataFrame([dict(ticker=t,session_close=d,close=100+i) for t in ["NVDA","SPY"] for i,d in enumerate(self.dates)])

    def test_strictly_later_entry_and_horizon(self):
        news = dict(id="a",ticker="NVDA",available_at=self.dates[0].isoformat())
        row = forward_returns(news,self.frame,1)[0]
        self.assertEqual(row["entry_at"],self.dates[1].isoformat())
        self.assertAlmostEqual(row["forward_return"],102/101-1)
        self.assertAlmostEqual(row["signed_net_return"],102/101-1-0.001)

    def test_censored_is_not_zero(self):
        news = dict(id="a",ticker="NVDA",available_at=self.dates[-2].isoformat())
        rows = forward_returns(news,self.frame,1)
        self.assertTrue(all(r["status"] == "right_censored" and r["forward_return"] is None for r in rows))

    def test_short_cost_and_neutral(self):
        n = dict(id="a",ticker="NVDA",available_at=self.dates[0].isoformat())
        r = forward_returns(n,self.frame,-1)[0]
        self.assertAlmostEqual(r["signed_net_return"],-(102/101-1)-0.001)
        self.assertEqual(forward_returns(n,self.frame,0)[0]["signed_net_return"],0)

    def test_schema_and_abstention(self):
        s = Signal(**offline_classifier({"text":"unconfirmed rumor of approval"},"v2"))
        self.assertEqual(position(s),0)
        with self.assertRaises(ValueError):
            Signal(**(s.model_dump() | {"confidence":1.1}))

    def test_cache_key_changes_with_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            called = []
            def f(p):
                called.append(1)
                return offline_classifier(p)
            for prompt in ["v1","v1","v2"]:
                structured_call(Signal,prompt,{"text":"earnings beat"},d,"offline","test",f)
            self.assertEqual(len(called),2)

    def test_naive_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"news.jsonl"
            p.write_text(json.dumps(dict(id="1",ticker="NVDA",text="news",published_at="2025-01-01",available_at="2025-01-02",source="test")))
            with self.assertRaises(ValueError): load_news(p)

    def test_future_prices_do_not_change_entry(self):
        n = dict(id="a",ticker="NVDA",available_at=self.dates[0].isoformat())
        before = forward_returns(n,self.frame,1)[0]
        self.frame.loc[self.frame.session_close > self.dates[2],"close"] *= 4
        after = forward_returns(n,self.frame,1)[0]
        self.assertEqual(before,after)

if __name__ == "__main__": unittest.main()
