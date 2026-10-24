from .utils import remove_unnecessary

class Embed:
    def __init__(
        self,
        title: str = "My embed",
        url: str | None = None,
        description: str | None = None,
        color: str = "#676767",
        timestamp: str | None = None
    ):
        self.title = title
        self.url = url
        self.description = description
        self.color = color
        self.timestamp = timestamp

        self.fields = []
        self.author = None
        self.footer = None

        self.image = None
        self.thumbnail = None

    def add_field(
        self,
        name: str = "My Field",
        value: str = "123",
        inline: bool = False
    ):
        self.fields.append(
            {"name": name, "value": value, "inline": inline}
        )

    def set_title(self, title: str):
        self.title = title
    def set_image(self, url: str):
        self.image = url
    def set_thumbnail(self, url: str):
        self.thumbnail = url
    def set_author(self, name: str, url: str):
        self.author = {"name": name, "icon_url": url}
    def set_footer(self, name: str, url: str):
        self.footer = {"text": name, "icon_url": url}
    def set_url(self, url: str):
        self.url = url
    def set_description(self, desc: str):
        self.description = desc
    def set_color(self, color: str):
        self.color = color
    def set_timestamp(self, timestamp: str):
        self.timestamp = timestamp
        
    def to_dict(self):
        return remove_unnecessary({
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "color": self.color,
            "author": self.author,
            "fields": self.fields,
            "thumbnail": self.thumbnail,
            "image": self.image,
            "footer": self.footer,
            "timestamp": self.timestamp
        })
