from PIL import Image


class DashboardPage:
    def __init__(self, image: Image) -> Image:
        self.image = image
        self.width, self.height = image.size

    def get_size(self):
        return self.image.size

    def get_graphic(self):
        x1 = 18
        y1 = 508
        x2 = 999
        y2 = 791
        return self.image.crop((x1, y1, x2, y2))

    def get_statuses(self):
        x1 = 1140
        y1 = 465
        x2 = 1755
        y2 = 810
        return self.image.crop((x1, y1, x2, y2))

    def get_custom_graphic(self):
        x1 = 10
        y1 = 110
        x2 = self.width
        y2 = self.height
        return self.image.crop((x1, y1, x2, y2))
