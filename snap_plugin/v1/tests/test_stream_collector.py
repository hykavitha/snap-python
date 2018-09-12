# -*- coding: utf-8 -*-
# http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import sys
import time

import grpc

import snap_plugin.v1 as snap
from snap_plugin.v1.collect_arg import CollectArg
from snap_plugin.v1.plugin_pb2 import StreamCollectorStub, Empty
from snap_plugin.v1.tests import ThreadPrinter

from .mock_plugins import MockStreamCollector


def test_monitor():
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 100}']
    col = MockStreamCollector("MyStreamCollector", 1)
    # with a PingTimeoutDuration at 50ms the plugin should shutdown
    # in just over 150ms
    col.start()
    assert col._shutting_down is False
    time.sleep(.4)
    assert col._shutting_down is True


def test_stream():
    sys.stdout = ThreadPrinter()
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 5000}']
    col = MockStreamCollector("MyStreamCollector", 99)
    col.start()
    t_end = time.time() + 5
    # wait for our collector to print its preamble
    while len(sys.stdout.lines) == 0 and time.time() < t_end:
        time.sleep(.1)
    resp = json.loads(sys.stdout.lines[0])
    client = StreamCollectorStub(
        grpc.insecure_channel(resp["ListenAddress"]))
    metric = snap.Metric(
        namespace=[snap.NamespaceElement(value="intel"),
                   snap.NamespaceElement(value="streaming"),
                   snap.NamespaceElement(value="random"),
                   snap.NamespaceElement(value="int")],
        version=1,
        unit="some unit",
        description="some description")
    mtr = iter([CollectArg(metric).pb])
    metrics = client.StreamMetrics(mtr)
    assert next(metrics).Metrics_Reply.metrics[0].int64_data == 200
    start_waiting_for_new_metric = time.time()
    assert next(metrics).Metrics_Reply.metrics[0].int64_data == 200
    retrieve_metric_time = time.time()
    assert round(retrieve_metric_time - start_waiting_for_new_metric) == 1
    col.stop()


def test_multiple_stream():
    sys.stdout = ThreadPrinter()
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 5000}']
    col = MockStreamCollector("MyStreamCollector", 99)
    col.start()
    t_end = time.time() + 5
    # wait for our collector to print its preamble
    while len(sys.stdout.lines) == 0 and time.time() < t_end:
        time.sleep(.1)
    resp = json.loads(sys.stdout.lines[0])
    client = StreamCollectorStub(
        grpc.insecure_channel(resp["ListenAddress"]))
    metric = snap.Metric(
        namespace=[snap.NamespaceElement(value="intel"),
                   snap.NamespaceElement(value="streaming"),
                   snap.NamespaceElement(value="random"),
                   snap.NamespaceElement(value="int")],
        version=1,
        unit="some unit",
        description="some description",
        config={"send_multiple": True}
    )
    mtr = iter([CollectArg(metric).pb])
    metrics = client.StreamMetrics(mtr)
    a = next(metrics)
    assert len(a.Metrics_Reply.metrics) == 3
    col.stop()


def test_stream_max_metrics_buffer():
    sys.stdout = ThreadPrinter()
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 5000}']
    col = MockStreamCollector("MyStreamCollector", 99)
    col.start()
    t_end = time.time() + 5
    # wait for our collector to print its preamble
    while len(sys.stdout.lines) == 0 and time.time() < t_end:
        time.sleep(.1)
    resp = json.loads(sys.stdout.lines[0])
    client = StreamCollectorStub(
        grpc.insecure_channel(resp["ListenAddress"]))
    metric = snap.Metric(
        namespace=[snap.NamespaceElement(value="intel"),
                   snap.NamespaceElement(value="streaming"),
                   snap.NamespaceElement(value="random"),
                   snap.NamespaceElement(value="int")],
        version=1,
        config={"max-metrics-buffer": 5},
        unit="some unit",
        description="some description")
    col_arg = CollectArg(metric).pb
    mtr = iter([col_arg])
    metrics = client.StreamMetrics(mtr)
    start_waiting_for_new_metric = time.time()
    a = next(metrics)
    retrieve_metric_time = time.time()
    assert round(retrieve_metric_time - start_waiting_for_new_metric) == 5
    assert len(a.Metrics_Reply.metrics) == 5
    col.stop()


def test_stream_max_collect_duration():
    sys.stdout = ThreadPrinter()
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 5000}']
    col = MockStreamCollector("MyStreamCollector", 99)
    col.start()
    t_end = time.time() + 5
    # wait for our collector to print its preamble
    while len(sys.stdout.lines) == 0 and time.time() < t_end:
        time.sleep(.1)
    resp = json.loads(sys.stdout.lines[0])
    client = StreamCollectorStub(
        grpc.insecure_channel(resp["ListenAddress"]))
    metric = snap.Metric(
        namespace=[snap.NamespaceElement(value="intel"),
                   snap.NamespaceElement(value="streaming"),
                   snap.NamespaceElement(value="random"),
                   snap.NamespaceElement(value="int")],
        version=1,
        config={
            "max-collect-duration": 2,
            "stream_delay": 3
        },
        unit="some unit",
        description="some description")
    col_arg = CollectArg(metric).pb
    mtr = iter([col_arg])
    metrics = client.StreamMetrics(mtr)
    start_waiting_for_new_metric = time.time()
    a = next(metrics)
    retrieve_metric_time = time.time()
    assert round(retrieve_metric_time - start_waiting_for_new_metric) == 2
    assert len(a.Metrics_Reply.metrics) == 0
    start_waiting_for_new_metric = time.time()
    a = next(metrics)
    retrieve_metric_time = time.time()
    assert round(retrieve_metric_time - start_waiting_for_new_metric) == 1
    assert len(a.Metrics_Reply.metrics) == 1
    col.stop()


def test_stream_max_metrics_buffer_with_max_collect_duration():
    sys.stdout = ThreadPrinter()
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 5000}']
    col = MockStreamCollector("MyStreamCollector", 99)
    col.start()
    t_end = time.time() + 5
    # wait for our collector to print its preamble
    while len(sys.stdout.lines) == 0 and time.time() < t_end:
        time.sleep(.1)
    resp = json.loads(sys.stdout.lines[0])
    client = StreamCollectorStub(
        grpc.insecure_channel(resp["ListenAddress"]))
    metric = snap.Metric(
        namespace=[snap.NamespaceElement(value="intel"),
                   snap.NamespaceElement(value="streaming"),
                   snap.NamespaceElement(value="random"),
                   snap.NamespaceElement(value="int")],
        version=1,
        config={
            "stream_delay": 3,
            "max-collect-duration": 4,
            "max-metrics-buffer": 3
        },
        unit="some unit",
        description="some description")
    col_arg = CollectArg(metric).pb
    mtr = iter([col_arg])
    metrics = client.StreamMetrics(mtr)
    start_waiting_for_new_metric = time.time()
    a = next(metrics)
    retrieve_metric_time = time.time()
    assert round(retrieve_metric_time - start_waiting_for_new_metric) == 4
    assert len(a.Metrics_Reply.metrics) == 1
    start_waiting_for_new_metric = time.time()
    a = next(metrics)
    retrieve_metric_time = time.time()
    assert round(retrieve_metric_time - start_waiting_for_new_metric) == 4
    assert len(a.Metrics_Reply.metrics) == 1
    col.stop()


def test_get_metric_types():
    from snap_plugin.v1.get_metrictypes_arg import GetMetricTypesArg
    sys.stdout = ThreadPrinter()
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 5000}']
    col = MockStreamCollector("MyStreamCollector", 99)
    col.start()
    t_end = time.time() + 5
    # wait for our collector to print its preamble
    while len(sys.stdout.lines) == 0 and time.time() < t_end:
        time.sleep(.1)
    resp = json.loads(sys.stdout.lines[0])
    client = StreamCollectorStub(
        grpc.insecure_channel(resp["ListenAddress"]))
    reply = client.GetMetricTypes(
        GetMetricTypesArg({}).pb)
    assert reply.error == ''
    assert len(reply.metrics) == 1
    assert reply.metrics[0].Version == 99
    col.stop()


def test_get_config_policy():
    sys.stdout = ThreadPrinter()
    sys.argv = ["", '{"LogLevel": 1, "PingTimeoutDuration": 5000}']
    col = MockStreamCollector("MyStreamCollector", 99)
    col.start()
    t_end = time.time() + 5
    # wait for our collector to print its preamble
    while len(sys.stdout.lines) == 0 and time.time() < t_end:
        time.sleep(.1)
    resp = json.loads(sys.stdout.lines[0])
    client = StreamCollectorStub(
        grpc.insecure_channel(resp["ListenAddress"]))
    reply = client.GetConfigPolicy(Empty())
    assert reply.error == ""
    assert reply.string_policy["intel.streaming.random"].rules["password"].default == "pass"
    col.stop()
