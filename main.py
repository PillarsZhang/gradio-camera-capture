from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import gradio as gr
import fire
from loguru import logger
import yaml

temp_manager = None
from temp_manager import TempManager

os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
import cv2
from cv2.typing import MatLike

MY_CV_DEFAULT_BACKEND = os.environ.get("MY_CV_DEFAULT_BACKEND", "CAP_ANY")
MY_CAMERA_CONFIG_YAML = os.environ.get("MY_CAMERA_CONFIG_YAML", "my_camera_config.yaml")
MY_FRAME_WATERMARK = os.environ.get("MY_FRAME_WATERMARK", "1")


@dataclass
class Camera:
    index: int
    backend: str
    frame_width: int
    frame_height: int
    fps: float

    def __repr__(self) -> str:
        return (
            f"{self.backend} Camera {self.index} - "
            f"{self.frame_width} x {self.frame_height} - {self.fps} fps"
        )

    def __post_init__(self):
        if not hasattr(cv2, self.backend):
            raise ValueError(f"Invalid backend: {self.backend}")

    def check(self):
        cap = cv2.VideoCapture(self.index, getattr(cv2, self.backend))
        ret = cap.isOpened()
        cap.release()
        return ret

    def init_cap(self):
        logger.debug(f"init_cap: {repr(self)}")
        cap = cv2.VideoCapture(self.index, getattr(cv2, self.backend))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.read()  # Warmup
        return cap

    @classmethod
    def scan(cls, index: int, backend: str = MY_CV_DEFAULT_BACKEND):
        cap = cv2.VideoCapture(index, getattr(cv2, backend))
        camera = None
        if cap.isOpened():
            camera = cls(
                index=index,
                backend=backend,
                frame_width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                frame_height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                fps=cap.get(cv2.CAP_PROP_FPS),
            )
        cap.release()
        return camera


def get_cameras(max_cameras: int = 8, backend: str = MY_CV_DEFAULT_BACKEND):
    """Detect available cameras and return a dictionary with descriptions and indices."""
    camera_dic: dict[str, Camera] = {}

    if (fn := Path(MY_CAMERA_CONFIG_YAML)).exists():
        with open(fn, "r") as f:
            my_camera_config: list[dict] = yaml.safe_load(f)
        logger.info(f"Check my cameras from {fn}")

        for c in my_camera_config:
            camera = Camera(**c)
            camera_key = f"*{repr(camera)}"
            camera_dic[camera_key] = camera
            logger.debug(f"Add {camera_key} to camera_dic")
            if camera.check():
                logger.success(f"Check passed")
            else:
                logger.warning(f"Check failed")

    logger.info(f"Scan cameras with {backend} backend")
    for index in range(max_cameras):
        if (camera := Camera.scan(index, backend)) is not None:
            camera_key = f"{repr(camera)}"
            camera_dic[camera_key] = camera
            logger.debug(f"Add {camera_key} to camera_dic")

    return camera_dic


TParseCameraInput = Camera | dict | tuple | int | str


def parse_camera(camera: TParseCameraInput) -> Camera:
    if isinstance(camera, Camera):
        return camera
    elif isinstance(camera, dict):
        return Camera(**camera)
    elif isinstance(camera, tuple):
        return Camera(*camera)
    elif isinstance(camera, (int, str)):
        return Camera.scan(int(camera))
    else:
        raise ValueError(f"Cannot parse camera: {camera}")


def add_watermark(frame: MatLike, position: tuple[int, int] = None):
    time_with_ms = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    frame = frame.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1
    thickness = 2
    if position is None:
        (text_width, text_height), _ = cv2.getTextSize(time_with_ms, font, scale, thickness)
        position = (
            int(frame.shape[1] * 0.95) - text_width,
            int(frame.shape[0] * 0.975) - text_height,
        )
    cv2.putText(frame, time_with_ms, position, font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return frame


def capture_image(
    output_file: str, camera: TParseCameraInput = 0, watermark: bool = MY_FRAME_WATERMARK
):
    """Capture an image from the specified camera and save it."""
    camera = parse_camera(camera)
    cap = camera.init_cap()

    logger.info(f"Begin capture {camera.frame_width} x {camera.frame_height} image")
    ret, frame = cap.read()
    cap.release()
    logger.debug(f"Cap released")
    if not ret:
        raise Exception(f"Capture image failed on {repr(camera)}")
    if watermark:
        frame = add_watermark(frame)
    ret = cv2.imwrite(output_file, frame)
    if not ret:
        raise Exception(f"Write image failed to output_file {output_file}")
    logger.debug(f"output_file: {output_file}")
    return output_file


def capture_video(
    output_file: str,
    camera: int = 0,
    video_length: int = 15,
    video_codec: str = "avc1",
    watermark: bool = MY_FRAME_WATERMARK,
):
    """Capture a video from the specified camera and save it."""
    camera = parse_camera(camera)
    cap = camera.init_cap()

    codec = cv2.VideoWriter_fourcc(*video_codec)
    out = cv2.VideoWriter(output_file, codec, camera.fps, (camera.frame_width, camera.frame_height))

    logger.info(
        f"Begin capture {camera.frame_width} x {camera.frame_height} - {camera.fps} fps video for {video_length} secs"
    )
    start_time = cv2.getTickCount()
    while (cv2.getTickCount() - start_time) / cv2.getTickFrequency() < video_length:
        ret, frame = cap.read()
        if not ret:
            raise Exception(f"Capture video failed on {repr(camera)}")
        if watermark:
            frame = add_watermark(frame)
        out.write(frame)
    cap.release()
    logger.debug(f"Cap released")

    out.release()
    logger.debug(f"output_file: {output_file}")
    return output_file


def launch_app(
    server_name="127.0.0.1", server_port=7860, auth: tuple[str, str] = None, show_error=True
):
    """Start the Gradio app with specified parameters."""

    camera_dic = get_cameras()
    camera_keys = list(camera_dic.keys())

    with gr.Blocks() as app:
        gr.Markdown(f"## Gradio Camera Capture Application")
        with gr.Row():
            camera_dropdown = gr.Dropdown(
                scale=3,
                label="Select Camera (or index)",
                choices=camera_keys,
                value=camera_keys[0],
                allow_custom_value=True,
            )
            video_length_number = gr.Number(
                scale=1,
                label="Video Length (seconds)",
                value=15,
                minimum=1,
                maximum=60,
            )
            with gr.Column(scale=1, min_width=160):
                capture_image_button = gr.Button("Capture Image")
                capture_video_button = gr.Button("Capture Video")

        with gr.Row():
            output_image = gr.Image()
            output_video = gr.Video(autoplay=True)

        def capture_image_api(camera_key: str):
            return capture_image(
                temp_manager.request_temp_file(suffix=".jpg"), camera_dic[camera_key]
            )

        capture_image_button.click(
            fn=capture_image_api,
            inputs=[camera_dropdown],
            outputs=[output_image],
        )

        def capture_video_api(camera_key: str, video_length: int):
            return capture_video(
                temp_manager.request_temp_file(suffix=".mp4"), camera_dic[camera_key], video_length
            )

        capture_video_button.click(
            fn=capture_video_api,
            inputs=[camera_dropdown, video_length_number],
            outputs=[output_video],
        )

        with TempManager() as temp_manager:
            app.launch(
                server_name=server_name, server_port=server_port, auth=auth, show_error=show_error
            )


if __name__ == "__main__":
    fire.Fire(
        {
            "app": launch_app,
            "cameras": get_cameras,
            "image": capture_image,
            "video": capture_video,
        }
    )
