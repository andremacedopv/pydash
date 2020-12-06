# Grupo 10 - TR1
# André Macedo - 170005950
# Danilo Inácio
# Felipe Lima

from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean


class R2ANewAlgoritm1(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.request_time = 0
        self.qi = []
        self.buffer_size = self.whiteboard.get_max_buffer_size()
        self.throughput = 0

        # Panda calculations variables
        self.download_duration = 0
        self.interrequest_time = 0
        self.bandwith_share = 0
        self.smoothed_bw = 0
        self.selected_qi = 0
        
        # Constants
        self.additive_increase = 300000
        self.convergence_rate = 0.14
        self.smoothing_rate = 0.2
        self.safety_margin = 0.15
        self.buffer_convergence = 0.2
        self.buffer_min = 5
        self.buffer_threshold = 0.5

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()

        self.send_down(msg)

    def handle_xml_response(self, msg):
        # Get quality values and define first selected quality
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        # Get first calculations for the algorithm
        self.download_duration = time.perf_counter() - self.request_time
        self.interrequest_time = self.download_duration
        self.throughput = msg.get_bit_length() / self.download_duration
        self.bandwith_share = self.throughput
        self.smoothed_bw = self.throughput

        # Get initial quality value
        for i in self.qi:
            if self.throughput/2 > i:
                self.selected_qi = i

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()

        # Step 1 - Estimate bandwith share:
        # Calculate the additive-increase-multiplicative-increase term 
        m = self.bandwith_share - self.throughput + self.additive_increase
        AIMD = self.convergence_rate * (self.additive_increase - max(0,m))

        # Calculate the bandwith share
        self.bandwith_share = self.bandwith_share + self.interrequest_time * AIMD
        # Fallback to throughput in case of negative value 
        if self.bandwith_share < 0:
            self.bandwith_share = self.throughput

        # Step 2 - Calculate the exponencial smoothing (EWMA):
        self.smoothed_bw = (-min(1,self.interrequest_time * self.smoothing_rate) * (self.smoothed_bw - self.bandwith_share)) + self.smoothed_bw

        # Step 3 - Implement the dead-zone quantifier
        # Calculate the upshift safety margin
        delta_up = self.safety_margin * self.smoothed_bw
        
        # Get possible qualities for the upshift and downshift threshold
        Rup = []
        Rdown = []
        for i in self.qi:
            if (i == self.qi[0]) or (i <= (self.smoothed_bw - delta_up)):
                Rup.append(i)
            if (i == self.qi[0]) or (i <= (self.smoothed_bw)):
                Rdown.append(i)
        # Get the best quality possible for the thresholds
        Rup = max(Rup)
        Rdown = max(Rdown)
        
        # Step 4 - Select the new quality
        new_qi = self.selected_qi
        if self.selected_qi < Rup:
            new_qi = Rup
        elif self.selected_qi <= Rdown:
            pass
        else:
            new_qi = Rdown
        
        # Change the quality only if it decreases or buffer is sufficiently full
        if len(self.whiteboard.get_playback_buffer_size()) > 0:
            buffer_size = self.whiteboard.get_playback_buffer_size()[-1][1]
        else:
            buffer_size = 0

        if (new_qi < self.selected_qi) or (buffer_size > self.whiteboard.get_max_buffer_size() * self.buffer_threshold):
            self.selected_qi = new_qi
        else:
            pass

        # Step 5 - Calculate the interrequest time
        # Calcutate the target interrequest
        target_interrequest = (self.selected_qi/self.smoothed_bw) + self.buffer_convergence * (buffer_size - self.buffer_min)

        # Select the interrequest as the highest among the target or the download duration
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
