# Grupo 10 - TR1
# André Macedo - 170005950
# Danilo Inácio
# Felipe Lima

from r2a.ir2a import IR2A
from player.parser import *
from base.whiteboard import Whiteboard
import time
from statistics import mean


class R2ANewAlgoritm1(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.request_time = 0
        self.qi = []
        self.buffer_size = self.whiteboard.get_max_buffer_size()

        self.throughput = 0
        self.download_duration = 0
        self.interrequest_time = 0
        self.bandwith_share = 0
        self.smoothed_bw = 0
        self.selected_qi = 0
        
        # Constants
        self.w = 300000
        self.k = 0.14
        self.smoothing_rate = 0.2
        self.safety_margin = 0.15
        self.buffer_convergence = 0.2
        self.buffer_min = 5

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):

        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()
        self.selected_qi = self.qi[0]

        self.download_duration = time.perf_counter() - self.request_time
        self.interrequest_time = self.download_duration
        self.throughput = msg.get_bit_length() / self.download_duration
        self.bandwith_share = self.throughput
        self.smoothed_bw = self.throughput

        self.send_up(msg)

    def handle_segment_size_request(self, msg):

        self.request_time = time.perf_counter()

        # Estimate bandwith share
        m = self.bandwith_share - self.throughput + self.w
        self.bandwith_share = self.bandwith_share + self.interrequest_time * self.k * (self.w - max(0,m))

        print(self.smoothed_bw)
        # Smoothing
        self.smoothed_bw = (-min(1,self.interrequest_time*self.smoothing_rate) * (self.smoothed_bw - self.bandwith_share)) + self.smoothed_bw

        # Quantization
        delta_up = self.safety_margin * self.smoothed_bw
        print(self.smoothed_bw)
        print(self.bandwith_share)
        print(self.interrequest_time)
        print(self.throughput)
        print(delta_up)
        Rup = max([i for i in self.qi if i <= (self.smoothed_bw - delta_up)])
        Rdown = max([i for i in self.qi if i <= (self.smoothed_bw)])
        print(Rup)
        print(Rdown)

        if self.selected_qi < Rup:
            self.selected_qi = Rup
        elif self.selected_qi <= Rdown:
            pass
        else:
            self.selected_qi = Rdown
        
        print(self.selected_qi)

        # Calculate target inter-request
        buffer = 0 if len(self.whiteboard.get_playback_buffer_size()) == 0 else self.whiteboard.get_playback_buffer_size()[-1][1]

        target_interrequest = (self.selected_qi/self.smoothed_bw) + self.buffer_convergence * (buffer - self.buffer_min)
        self.interrequest_time = max(target_interrequest, self.download_duration)

        msg.add_quality_id(self.selected_qi)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.download_duration = time.perf_counter() - self.request_time
        self.throughput = msg.get_bit_length() / self.download_duration
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
