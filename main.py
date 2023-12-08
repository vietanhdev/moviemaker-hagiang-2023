from multiprocessing import freeze_support

import cv2

from movie_maker import TimeLapsMovieMaker

if __name__ == '__main__':
    freeze_support()

    # Initialize movie maker
    movie_maker = TimeLapsMovieMaker(
        tmp_dir="outputs",
    )
    movie_maker.start_capture()

    # Show full screen window
    cv2.namedWindow("Image", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Image", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        live_frame = movie_maker.render_live_frame()
        if live_frame is None:
            continue

        cv2.imshow('Image', live_frame)
        c = cv2.waitKey(1)
        if c == ord('q'):  # Exit when user press "q"
            movie_maker.stop_capture()
            break
        elif c ==  32: # Space
            movie_maker.capture_frame()
        elif c == ord('p'):
            movie_maker.playback()
        elif c == ord('w'):
            movie_maker.output_video()
