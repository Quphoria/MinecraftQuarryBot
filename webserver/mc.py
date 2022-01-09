from dataclasses import dataclass
import math

mod = "opencomputers"

@dataclass
class Pos:
    x: int
    y: int
    z: int

    @staticmethod
    def from_str(s):
        x, y, z = s.split(", ", 2)
        x = math.floor(float(x))
        y = math.floor(float(y))
        z = math.floor(float(z))
        return Pos(x, y, z)

    @staticmethod
    def from_list(l):
        return Pos(l[0], l[1], l[2])

    def to_list(self):
        return [self.x, self.y, self.z]

    def __add__(self, p: 'Pos') -> 'Pos':
        return Pos(self.x + p.x, self.y + p.y, self.z + p.z)

    def __sub__(self, p: 'Pos') -> 'Pos':
        return Pos(self.x - p.x, self.y - p.y, self.z - p.z)

    def __abs__(self) -> int:
        return abs(self.x) + abs(self.y) + abs(self.z)

    def __eq__(self, p: 'Pos') -> bool:
        if type(p) != self.__class__:
            return False
        return self.x == p.x and self.y == p.y and self.z == p.z

    def manhattan_distance(self, p: 'Pos') -> int:
        return abs(self - p)

    def copy(self) -> 'Pos':
        return Pos(self.x, self.y, self.z)

    def to_str(self) -> str:
        return f"{self.x}, {self.y}, {self.z}"
