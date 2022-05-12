import os
import pathlib
import tempfile
import time
import uuid
from multiprocessing import Process, Queue

import cv2

from config import MAX_QUEUE_SIZE


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
        file_path = os.path.join(self.tmp_dir, str(uuid.uuid4()) + ".mp4")
        out = cv2.VideoWriter(file_path, cv2.VideoWriter_fourcc(*'MP4V'), self.playback_fps, (frame_width, frame_height))
        self.writing_frame_id = 0
        self.mode = "WRITING_VIDEO"
        for self.writing_frame_id in range(len(self.captured_frames)):
            out.write(self.captured_frames[self.writing_frame_id])
        out.release()
        self.mode = "LIVE"

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
        return draw

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
            self.enqueue_frame(frame)

    def render_info(self, frame):
        """Render metadata info to frame"""

        # Print captured frames
        text = "Captured: {} - Mode: {}".format(len(self.captured_frames), self.mode)
        if self.mode == "WRITING_VIDEO":
            text += " - Writing: {}/{}".format(self.writing_frame_id, len(self.captured_frames))
        cv2.putText(frame, text,
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)