import os


class FileManager:
    @staticmethod
    def create_dir(path: str):
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def get_session_dirs(base_dir: str):
        FileManager.create_dir(base_dir)
        # Identify existing session directories (only digits)
        session_ids = [int(x) for x in os.listdir(base_dir) if x.isdigit()]
        new_id = max(session_ids, default=0) + 1
        session_dir = os.path.join(base_dir, str(new_id))
        task_dir = os.path.join(session_dir, "task")
        restore_dir = os.path.join(session_dir, "restore")
        FileManager.create_dir(task_dir)
        FileManager.create_dir(restore_dir)
        return session_dir, task_dir, restore_dir

    @staticmethod
    def create_video_dirs(output_dir: str):
        video_dir = os.path.join(output_dir, "Video")
        bottom_video_dir = os.path.join(output_dir, "Bottom_Video")
        FileManager.create_dir(video_dir)
        FileManager.create_dir(bottom_video_dir)
        return video_dir, bottom_video_dir

    @staticmethod
    def create_image_dirs(output_dir: str):
        image_dir = os.path.join(output_dir, "Images")
        bottom_image_dir = os.path.join(output_dir, "Bottom_Images")
        FileManager.create_dir(image_dir)
        FileManager.create_dir(bottom_image_dir)
        return image_dir, bottom_image_dir
