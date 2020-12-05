# Grupo 10 - TR1
# André Macedo - 170005950
# Danilo Inácio
# Felipe Lima

from r2a.ir2a import IR2A
from player.parser import *
from base.whiteboard import Whiteboard
import time
from statistics import mean


class R2ANewAlgoritm2(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.throughputs = []
        self.request_time = 0
        self.qi = []

        # starts with the worst quality
        self.index_selected_qi = 0

        # range of throughputs analyzed
        self.M = 5

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # Round Trip Time
        RTT = time.perf_counter() - self.request_time
        RTT /= 2
        if len(self.throughputs) == self.M:
            self.throughputs.pop(0)
            self.throughputs.append(msg.get_bit_length()/RTT)
        else:
            self.throughputs.append(msg.get_bit_length()/RTT)
        
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        # time to define the segment quality choose to make the request

        # estimate the possibility to increase or decrease quality
        avg_throughput = mean(self.throughputs)
        sigma2 = sum([abs((i * (self.throughputs[i] - avg_throughput))) for i in range(len(self.throughputs))]) / len(self.throughputs)
        p = (avg_throughput) / (avg_throughput + sigma2)
        tau = (1 - p) * self.qi[max(0, self.index_selected_qi - 1)]
        theta = p * self.qi[min(len(self.qi) - 1, self.index_selected_qi + 1)]

        # selects the closest qi to tau + theta
        diff_list = [abs(qi - tau + theta) for qi in self.qi] 
        self.index_selected_qi = diff_list.index(min(diff_list))

        msg.add_quality_id(self.qi[self.index_selected_qi])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        # Round Trip Time
        RTT = time.perf_counter() - self.request_time
        RTT /= 2
        if len(self.throughputs) == self.M:
            self.throughputs.pop(0)
            self.throughputs.append(msg.get_bit_length()/RTT)
        else:
            self.throughputs.append(msg.get_bit_length()/RTT)

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass