import os
import pathlib
import tempfile
import time
import imutils
import numpy as np
from multiprocessing import Process, Queue
from datetime import datetime
import requests
from threading import Thread

import cv2

from config import MAX_QUEUE_SIZE


extended_width = 400
banner_image = cv2.imread("maylamphim.png")
banner_image = imutils.resize(banner_image, width = extended_width)
banner_height, banner_width = banner_image.shape[:2]
instruction_image = cv2.imread("instruction.png")
instruction_image = imutils.resize(instruction_image, width = extended_width)
download_image = cv2.imread("download.png")
download_image = imutils.resize(download_image, width = extended_width)

def upload_movie(path):
    url = "http://15.165.75.234/upload-file-1eb/"
    files = {'file': open(path, 'rb')}
    r = requests.post(url, files=files)

class TimeLapsMovieMaker:
    """TimeLaps Movie Maker"""

    def __init__(self, tmp_dir=None):
        self.frames = Queue(maxsize=MAX_QUEUE_SIZE)
        self.captured_frames = []
        self.playback_fps = 8

        if tmp_dir is not None:
            self.tmp_dir = tmp_dir
            if not os.path.exists(self.tmp_dir):
                pathlib.Path(self.tmp_dir).mkdir(parents=True, exist_ok=True)
        else:
            self.tmp_dir = tempfile.mkdtemp()

        self.mode = "LIVE"  # LIVE/PLAYBACK
        self.begin_playback_time = time.time()
        self.writing_frame_id = 0

    def playback(self):
        """Playback movie"""
        self.begin_playback_time = time.time()
        self.mode = "PLAYBACK"

    def output_video(self):
        """Output video from captured frames"""
        if len(self.captured_frames) == 0:
            return
        frame_width = self.captured_frames[0].shape[1]
        frame_height = self.captured_frames[0].shape[0]
        print(frame_width)
        print(frame_height)
        now = datetime.now()
        dt_string = now.strftime("%Y_%m_%d_%H_%M_%S")
        file_path = os.path.join(self.tmp_dir, dt_string + ".mp4")
        out = cv2.VideoWriter(file_path, cv2.VideoWriter_fourcc('a', 'v', 'c', '1'), self.playback_fps, (frame_width, frame_height))
        self.writing_frame_id = 0
        self.mode = "WRITING_VIDEO"
        for self.writing_frame_id in range(len(self.captured_frames)):
            out.write(self.captured_frames[self.writing_frame_id])
        out.release()
        self.mode = "LIVE"
        self.captured_frames = []
        
        # Upload
        thread = Thread(target=upload_movie, args=(file_path, ))
        thread.start()
        

    def capture_frame(self):
        """Capture frame from frame queue"""
        frame = self.frames.get()
        self.captured_frames.append(frame)

    def enqueue_frame(self, frame):
        """Enqueue frame from camera source"""
        if self.frames.full():
            self.frames.get()
        self.frames.put(frame)

    def render_live_frame(self):
        """Render live frame to screen"""
        extended_width = 300
        banner_image
        draw = None
        if self.mode == "LIVE":
            draw = self.frames.get()
            if len(self.captured_frames) > 0:
                draw = cv2.addWeighted(draw, 0.6, self.captured_frames[-1], 0.4, 0)
        elif self.mode == "PLAYBACK":
            current_time = time.time()
            frame_id = int(self.playback_fps *
                           (current_time - self.begin_playback_time))
            if frame_id < len(self.captured_frames):
                draw = self.captured_frames[frame_id].copy()
            else:
                self.mode = "LIVE"
                draw = self.render_live_frame()
        elif self.mode == "WRITING_VIDEO":
            draw = self.captured_frames[self.writing_frame_id].copy()

        self.render_info(draw)
        draw = self.render_banner(draw)
        
        return draw
    
    def render_banner(self, draw):
        if draw is None:
            return draw
        height, width = draw.shape[:2]
        new_width = width + extended_width
        screen = np.zeros((height, new_width, 3), dtype=np.uint8)
        screen[:banner_height, width:new_width, :] = banner_image
        screen[banner_height:2*banner_height, width:new_width, :] = instruction_image
        screen[2*banner_height:3*banner_height, width:new_width, :] = download_image
        screen[:, :width] = draw
        return screen

    def start_capture(self):
        """Start capturing process to get frame from camera"""
        self.capture_process = Process(target=self.capture_loop)
        self.capture_process.start()

    def stop_capture(self):
        """Stop capturing process"""
        self.capture_process.terminate()

    def capture_loop(self):
        """Capturing loop"""
        vid = cv2.VideoCapture(0)
        while True:
            _, frame = vid.read()
            frame = imutils.resize(frame, height=720)
            self.enqueue_frame(frame)

    def render_info(self, frame):
        """Render metadata info to frame"""

        # Print captured frames
        text = "Captured: {} - Mode: {}".format(len(self.captured_frames), self.mode)
        if self.mode == "WRITING_VIDEO":
            text += " - Writing: {}/{}".format(self.writing_frame_id, len(self.captured_frames))
        cv2.putText(frame, text,
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2, cv2.LINE_AA)