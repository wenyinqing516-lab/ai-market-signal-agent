import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from pydantic import BaseModel
from src.llm import structured_call

class Output(BaseModel):
    value: int

class AdapterTests(unittest.TestCase):
    def fake_module(self, parse):
        class StatusError(Exception):
            status_code = 500
        class RateLimitError(StatusError): pass
        class ConnectionError(StatusError): pass
        return types.SimpleNamespace(OpenAI=lambda **kwargs: types.SimpleNamespace(responses=types.SimpleNamespace(parse=parse)),
                                     RateLimitError=RateLimitError, APIConnectionError=ConnectionError, APIStatusError=StatusError)

    def test_live_adapter_contract_without_network(self):
        calls=[]
        def parse(**kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(output_parsed=Output(value=7),usage=None)
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{"OPENAI_API_KEY":"mock-only"}), patch.dict(sys.modules,{"openai":self.fake_module(parse)}):
            result,meta=structured_call(Output,"instructions",{"x":1},d,"openai","mock-model",None)
        self.assertEqual(result.value,7)
        self.assertFalse(calls[0]["store"])
        self.assertEqual(calls[0]["text_format"],Output)
        self.assertEqual(meta["attempts"],1)

    def test_refusal_is_failure_not_offline_fallback(self):
        parse=lambda **kwargs: types.SimpleNamespace(output_parsed=None)
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{"OPENAI_API_KEY":"mock-only"}), patch.dict(sys.modules,{"openai":self.fake_module(parse)}):
            with self.assertRaises(ValueError):
                structured_call(Output,"p",{},d,"openai","mock-model",lambda _: {"value":99})

    def test_retry_is_bounded(self):
        calls=[]
        fake=self.fake_module(None)
        def parse(**kwargs):
            calls.append(1)
            raise fake.RateLimitError()
        fake.OpenAI=lambda **kwargs: types.SimpleNamespace(responses=types.SimpleNamespace(parse=parse))
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{"OPENAI_API_KEY":"mock-only"}), patch.dict(sys.modules,{"openai":fake}), patch("src.llm.time.sleep"):
            with self.assertRaises(fake.RateLimitError):
                structured_call(Output,"p",{},d,"openai","mock-model",None)
        self.assertEqual(len(calls),3)
