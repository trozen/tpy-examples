import math
from struct import unpack_from
import random

from typing import Final

from tpy import Int32, Own, Ptr, UInt8, readonly
from tplib import Box

# Annotated so they can be imported: an unannotated module-level variable is
# not exported in TurboPython 0.5.1.
WIDTH: Final[Int32] = 800
HEIGHT: Final[Int32] = 600

WIDTH_2 = WIDTH//2
HEIGHT_2 = HEIGHT//2
HEIGHT_INV: Final[float] = 1.0 / WIDTH

TAN_45_DEG = math.tan(math.radians(45))

FLOOR_Y_INV = [1.0 / (y - HEIGHT_2) if y > HEIGHT_2 else 0.0
               for y in range(HEIGHT)]

CEIL_Y_INV = [1.0 / (HEIGHT_2 - y) if y < HEIGHT_2 else 0.0
              for y in range(HEIGHT)]

OSCILLATION = [Int32(13 + 13 * math.sin(2 * math.pi * (i / 255)))
               for i in range(256)]


class Vertex:
    x: Int32
    y: Int32

    def __init__(self, x: Int32, y: Int32) -> None:
        self.x = x
        self.y = y


class Sidedef:
    offset_x: Int32
    offset_y: Int32
    # Ptr: the Map owns the textures and sectors; a sidedef only refers to them.
    # Ptr is nullable, which also covers the missing-texture case.
    upper_texture: Ptr[Texture]
    lower_texture: Ptr[Texture]
    middle_texture: Ptr[Texture]
    sector: Ptr[Sector]
    skyhack: bool

    def __init__(self, offset_x: Int32, offset_y: Int32,
                 upper_texture: Ptr[Texture], lower_texture: Ptr[Texture],
                 middle_texture: Ptr[Texture], sector: Ptr[Sector]) -> None:
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.upper_texture = upper_texture
        self.lower_texture = lower_texture
        self.middle_texture = middle_texture
        self.sector = sector
        self.skyhack = False


class Linedef:
    vertex_start: Ptr[Vertex]
    vertex_end: Ptr[Vertex]
    special_type: Int32
    sidedef_front: Ptr[Sidedef]
    sidedef_back: Ptr[Sidedef]

    def __init__(self, vertex_start: Ptr[Vertex], vertex_end: Ptr[Vertex],
                 special_type: Int32, sidedef_front: Ptr[Sidedef],
                 sidedef_back: Ptr[Sidedef]) -> None:
        self.vertex_start = vertex_start
        self.vertex_end = vertex_end
        self.special_type = special_type
        self.sidedef_front = sidedef_front
        self.sidedef_back = sidedef_back


# Moved ahead of Sector: Sector stores a Flat and a Picture by value, and
# generated classes appear in source order with no forward declarations.
class Flat:
    data: list[list[list[Int32]]]

    def __init__(self, data: list[bytes]) -> None:
        self.data = [[[d[64*y+x] for y in range(64)]
                     for x in range(64)] for d in data]

    def get_data(self, frame_count: Int32) -> list[list[Int32]]:
        return self.data[(frame_count >> 4) % len(self.data)]


class Picture:
    width: Int32
    height: Int32
    data: list[list[Int32]]

    def __init__(self, data: bytes) -> None:
        # struct.unpack_from yields exactly-sized types (UInt16/UInt8 here), so
        # the values are widened to Int32 before they meet ordinary arithmetic.
        width = Int32(unpack_from('<HHhh', data, 0)[0])
        height = Int32(unpack_from('<HHhh', data, 0)[1])
        self.width = width
        self.height = height
        self.data = [[0 for k in range(height)] for j in range(width)]

        for j in range(width):
            col_offset = Int32(unpack_from('<H', data, 8+4*j)[0])
            y_offset = Int32(unpack_from('<B', data, col_offset)[0])
            length = Int32(unpack_from('<BB', data, col_offset+1)[0])
            for y in range(length):
                self.data[j][y+y_offset] = data[col_offset+3+y]


class Sector:
    floor_h: Int32
    ceil_h: Int32
    floor_texture: bytes
    ceil_texture: bytes
    light_level: Int32
    special_type: Int32
    floor_flat: Flat
    ceil_flat: Flat
    ceil_pic: Picture | None
    random: list[bool]

    def __init__(self, floor_h: Int32, ceil_h: Int32, floor_texture: bytes,
                 ceil_texture: bytes, light_level: Int32, special_type: Int32,
                 floor_flat: Own[Flat], ceil_flat: Own[Flat],
                 ceil_pic: Own[Picture] | None) -> None:
        self.floor_h = floor_h
        self.ceil_h = ceil_h
        self.floor_texture = floor_texture
        self.ceil_texture = ceil_texture
        self.light_level = light_level
        self.special_type = special_type
        self.floor_flat = floor_flat
        self.ceil_flat = ceil_flat
        self.ceil_pic = ceil_pic

        self.random = [random.random() < 0.5 for i in range(256)]


class SubSector:
    segs: list[Ptr[Seg]]

    def __init__(self, segs: Own[list[Ptr[Seg]]]) -> None:
        self.segs = segs


class Seg:
    vertex_start: Ptr[Vertex]
    vertex_end: Ptr[Vertex]
    angle: Int32
    linedef: Ptr[Linedef]
    sidedef_front: Ptr[Sidedef]
    sidedef_back: Ptr[Sidedef]
    is_portal: bool
    offset: Int32
    sector_front: Ptr[Sector]
    sector_back: Ptr[Sector]
    length: float

    def __init__(self, vertex_start: Ptr[Vertex], vertex_end: Ptr[Vertex],
                 angle: Int32, linedef: Ptr[Linedef],
                 sidedef_front: Ptr[Sidedef], sidedef_back: Ptr[Sidedef],
                 is_portal: bool, offset: Int32,
                 sector_front: Ptr[Sector], sector_back: Ptr[Sector]) -> None:
        self.vertex_start = vertex_start
        self.vertex_end = vertex_end
        self.angle = angle
        self.linedef = linedef
        self.sidedef_front = sidedef_front
        self.sidedef_back = sidedef_back
        self.is_portal = is_portal
        self.offset = offset
        self.sector_front = sector_front
        self.sector_back = sector_back

        self.length = math.hypot(vertex_end.x - vertex_start.x,
                                 vertex_end.y - vertex_start.y)


class BSPNode:
    partition_x: Int32
    partition_y: Int32
    change_partition_x: Int32
    change_partition_y: Int32
    rchild_id: Int32
    lchild_id: Int32

    def __init__(self, partition_x: Int32, partition_y: Int32,
                 change_partition_x: Int32, change_partition_y: Int32,
                 rchild_id: Int32, lchild_id: Int32) -> None:
        self.partition_x = partition_x
        self.partition_y = partition_y
        self.change_partition_x = change_partition_x
        self.change_partition_y = change_partition_y
        self.rchild_id = rchild_id
        self.lchild_id = lchild_id

    # The original defaults subsectors to None and allocates on first call.
    # Here the caller owns the list and it is filled in place, which avoids an
    # optional owning parameter and one allocation per frame.
    def visit(self, map_: Ptr[Map], subsectors: list[Ptr[SubSector]]) -> None:
        player = map_.player
        px = player.x - self.partition_x
        py = player.y - self.partition_y

        closest_id, farthest_id = self.lchild_id, self.rchild_id
        if py * self.change_partition_x <= px * self.change_partition_y:
            closest_id, farthest_id = farthest_id, closest_id

        for child_id in [closest_id, farthest_id]:
            if child_id < 0:
                subsectors.append(map_.subsectors[child_id & 0x7fff])
            else:
                map_.bspnodes[child_id].visit(map_, subsectors)


class Thing:
    x: float
    y: float
    angle: float
    type_: Int32

    def __init__(self, x: Int32, y: Int32, angle: Int32, type_: Int32) -> None:
        self.x = float(x)
        self.y = float(y)
        self.angle = math.radians(90)
        self.type_ = type_


class Vec2:
    x: float
    y: float

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def dot(self, v: Vec2) -> float:
        return self.x * v.x + self.y * v.y


class Player:
    x: float
    y: float
    z: float
    angle: float
    floor_h: float
    direction: Vec2

    def __init__(self, thing: Thing) -> None:
        self.x = thing.x
        self.y = thing.y
        self.z = 0.0
        self.angle = thing.angle
        self.floor_h = 48.0
        self.direction = Vec2(math.cos(self.angle), math.sin(self.angle))

    def update(self) -> None:
        self.direction = Vec2(math.cos(self.angle), math.sin(self.angle))


class Texture:
    name: bytes
    data: list[list[Int32]]
    width: Int32
    height: Int32

    def __init__(self, name: bytes, data: Own[list[list[Int32]]],
                 width: Int32, height: Int32) -> None:
        self.name = name
        self.data = data
        self.width = width
        self.height = height


class Colormap:
    data: list[Int32]

    def __init__(self, data: bytes) -> None:
        self.data = []
        for i in range(256):
            self.data.append(data[i])


class Map:
    entry_data: dict[bytes, bytes]
    palette: list[tuple[Int32, Int32, Int32]]
    colormaps: list[Colormap]
    patches: list[Picture | None]
    textures: dict[bytes, Texture]
    vertices: list[Vertex]
    sectors: list[Sector]
    sidedefs: list[Sidedef]
    linedefs: list[Linedef]
    segs: list[Seg]
    subsectors: list[SubSector]
    bspnodes: list[BSPNode]
    things: list[Thing]
    player: Player

    def __init__(self, filepath: str, map_: str) -> None:
        # Each extract_ method below fills its own field, but a field first
        # assigned in a callee is default-constructed rather than initialized,
        # which is a divergence from CPython (where the attribute would simply
        # not exist yet). Stating the empty value here makes that explicit.
        self.entry_data = {}
        self.palette = []
        self.colormaps = []
        self.patches = []
        self.textures = {}
        self.vertices = []
        self.sectors = []
        self.sidedefs = []
        self.linedefs = []
        self.segs = []
        self.subsectors = []
        self.bspnodes = []
        self.things = []

        self.extract_entries(filepath, map_)

        self.extract_palette()
        self.extract_colormaps()
        self.extract_patches()
        self.extract_textures()
        self.extract_vertices()
        self.extract_sectors()
        self.extract_sidedefs()
        self.extract_linedefs()
        self.extract_segs()
        self.extract_subsectors()
        self.extract_bspnodes()
        self.extract_things()

        self.player = Player(self.things[0])

    def extract_entries(self, filepath: str, mapname: str) -> None:
        data = open(filepath, 'rb').read()
        nentries = Int32(unpack_from('<II', data, 4)[0])
        dir_offset = Int32(unpack_from('<II', data, 4)[1])

        self.entry_data = {}
        inmap = False
        bmapname = bytes([ord(c) for c in mapname])  # TODO encoding='acscii'?

        # filter entries that apply to map
        for i in range(nentries):
            offset_u, length_u, name = unpack_from('<II8s', data, dir_offset+i*16)
            offset = Int32(offset_u)
            length = Int32(length_u)
            # rstrip yields a non-owning view; an owned copy is needed to store
            # it and to look it up in a dict[bytes, ...].
            name = bytes(name.rstrip(b'\0'))

            if name == bmapname:
                inmap = True
            elif ((inmap or name in (b'PLAYPAL', b'COLORMAP')) and
                    name not in self.entry_data):
                # a bytes slice is a non-owning view; store an owned copy
                self.entry_data[name.upper()] = bytes(data[offset: offset+length])

    def extract_vertices(self) -> None:
        self.vertices = []
        data = self.entry_data[b'VERTEXES']
        for j in range(len(data)//4):
            x_u, y_u = unpack_from('<hh', data, j*4)
            x = Int32(x_u)
            y = Int32(y_u)
            self.vertices.append(Vertex(x, y))

    def extract_linedefs(self) -> None:
        self.linedefs = []
        data = self.entry_data[b'LINEDEFS']
        for j in range(len(data)//14):
            (vs_u, ve_u, _, st_u, _, sf_u, sb_u) = \
                unpack_from('<HHHHHHH', data, j*14)
            vertex_start = Int32(vs_u)
            vertex_end = Int32(ve_u)
            special_type = Int32(st_u)
            sidedef_front = Int32(sf_u)
            sidedef_back = Int32(sb_u)
            vertex_a = self.vertices[vertex_start]
            vertex_b = self.vertices[vertex_end]
            sidedef_a = self.sidedefs[sidedef_front]
            # Ptr is nullable, so the "no back sidedef" case needs no Optional.
            sidedef_b: Ptr[Sidedef] = None
            if sidedef_back != 0xffff:
                sidedef_b = self.sidedefs[sidedef_back]
            linedef = Linedef(vertex_a, vertex_b, special_type,
                              sidedef_a, sidedef_b)
            self.linedefs.append(linedef)

        # sky hack
        for linedef in self.linedefs:
            if (linedef.sidedef_front is not None and
                    linedef.sidedef_front.sector.ceil_pic is not None and
                    linedef.sidedef_back is not None and
                    linedef.sidedef_back.sector.ceil_pic is not None):
                linedef.sidedef_front.skyhack = True

    def extract_sidedefs(self) -> None:
        self.sidedefs = []
        data = self.entry_data[b'SIDEDEFS']
        for j in range(len(data)//30):
            (ox_u, oy_u, upper_texture_name, lower_texture_name,
                middle_texture_name, sector_nr_u) = \
                    unpack_from('<HH8s8s8sH', data, j*30)
            offset_x = Int32(ox_u)
            offset_y = Int32(oy_u)
            sector_nr = Int32(sector_nr_u)

            # Ptr into the Map-owned texture table; .get() would yield a value.
            upper_texture: Ptr[Texture] = None
            lower_texture: Ptr[Texture] = None
            middle_texture: Ptr[Texture] = None
            upper_name = bytes(upper_texture_name.rstrip(b'\0'))
            lower_name = bytes(lower_texture_name.rstrip(b'\0'))
            middle_name = bytes(middle_texture_name.rstrip(b'\0'))
            if upper_name in self.textures:
                upper_texture = self.textures[upper_name]
            if lower_name in self.textures:
                lower_texture = self.textures[lower_name]
            if middle_name in self.textures:
                middle_texture = self.textures[middle_name]
            sector = self.sectors[sector_nr]
            sidedef = Sidedef(offset_x, offset_y, upper_texture, lower_texture,
                              middle_texture, sector)
            self.sidedefs.append(sidedef)

    def extract_sectors(self) -> None:
        self.sectors = []
        data = self.entry_data[b'SECTORS']
        for j in range(len(data)//26):
            (fh_u, ch_u, floor_texture, ceil_texture, ll_u, st_u, _) = \
                    unpack_from('<hh8s8sHhh', data, j*26)
            floor_h = Int32(fh_u)
            ceil_h = Int32(ch_u)
            light_level = Int32(ll_u)
            special_type = Int32(st_u)
            light_level &= 0xff
            floor_texture = bytes(floor_texture.rstrip(b'\0'))
            if floor_texture.startswith(b'NUKAGE'):
                names = [b'NUKAGE1', b'NUKAGE2', b'NUKAGE3']
                floor_flat = Flat([self.entry_data[name] for name in names])
            else:
                floor_flat = Flat([self.entry_data[floor_texture]])
            ceil_texture = bytes(ceil_texture.rstrip(b'\0'))
            ceil_flat = Flat([self.entry_data[ceil_texture]])
            ceil_pic = None
            if b'F_SKY' in ceil_texture:
                pic_data = self.entry_data[ceil_texture.replace(b'F_', b'')]
                ceil_pic = Picture(pic_data)
            sector = Sector(floor_h, ceil_h, floor_texture, ceil_texture,
                            light_level, special_type, floor_flat, ceil_flat,
                            ceil_pic)
            self.sectors.append(sector)

    def extract_patches(self) -> None:
        self.patches = []
        data = self.entry_data[b'PNAMES']
        n_pnames = Int32(unpack_from('<i', data, 0)[0])
        for j in range(n_pnames):
            patch_name = bytes(data[4+j*8:4+(j+1)*8].rstrip(b'\0').upper())
            patch: Picture | None = None
            try:
                patch = Picture(self.entry_data[patch_name])
            except KeyError:
                patch = None
            self.patches.append(patch)

    def extract_textures(self) -> None:
        self.textures = {}
        data = self.entry_data[b'TEXTURE1']
        n_textures = Int32(unpack_from('<i', data, 0)[0])
        for j in range(n_textures):
            offset = Int32(unpack_from('<i', data, 4+j*4)[0])
            (name, _, width_u, height_u, _, n_patches_u) = \
                unpack_from('<8sIHHIH', data, offset)
            width = Int32(width_u)
            height = Int32(height_u)
            n_patches = Int32(n_patches_u)
            # rstrip yields a non-owning view; an owned copy is needed to store
            # it and to look it up in a dict[bytes, ...].
            name = bytes(name.rstrip(b'\0'))
            patch = [[0 for k in range(height)] for j in range(width)]
            for k in range(n_patches):
                ox_u, oy_u, pi_u, _, _ = \
                    unpack_from('<hhhhh', data, offset+22+k*10)
                offset_x = Int32(ox_u)
                offset_y = Int32(oy_u)
                patch_index = Int32(pi_u)
                pic = self.patches[patch_index]
                # A PNAMES entry with no matching lump stays None; a texture
                # referencing one would be a malformed WAD.
                assert pic is not None
                for m in range(pic.width):
                    for n in range(pic.height):
                        x = m+offset_x
                        y = n+offset_y
                        if 0 <= x < width and 0 <= y < height:
                            patch[x][y] = pic.data[m][n]
            self.textures[name] = Texture(name, patch, width, height)

    def extract_palette(self) -> None:
        self.palette = []
        data = self.entry_data[b'PLAYPAL']
        for j in range(256):
            r_u, g_u, b_u = unpack_from('<BBB', data, 3*j)
            r = Int32(r_u)
            g = Int32(g_u)
            b = Int32(b_u)
            self.palette.append((r, g, b))

    def extract_colormaps(self) -> None:
        self.colormaps = []
        data = self.entry_data[b'COLORMAP']
        for j in range(34):
            self.colormaps.append(Colormap(bytes(data[256*j:256*(j+1)])))

    def extract_segs(self) -> None:
        self.segs = []
        data = self.entry_data[b'SEGS']
        for j in range(len(data)//12):
            vs_u, ve_u, angle_u, ln_u, dir_u, off_u = \
                unpack_from('<HHhHHh', data, j*12)
            vertex_start = Int32(vs_u)
            vertex_end = Int32(ve_u)
            angle = Int32(angle_u)
            linedef_nr = Int32(ln_u)
            direction = Int32(dir_u)
            offset = Int32(off_u)
            vertex_a = self.vertices[vertex_start]
            vertex_b = self.vertices[vertex_end]
            linedef = self.linedefs[linedef_nr]
            sidedef_back = None
            is_portal = False
            if direction == 0:
                sidedef_front = linedef.sidedef_front
                if linedef.sidedef_back is not None:
                    sidedef_back = linedef.sidedef_back
                    is_portal = True
            else:
                sidedef_front = linedef.sidedef_back
                if linedef.sidedef_front is not None:
                    sidedef_back = linedef.sidedef_front
                    is_portal = True
            sector_front = sidedef_front.sector
            if sidedef_back is not None:
                sector_back = sidedef_back.sector
            else:
                sector_back = None
            self.segs.append(Seg(vertex_a, vertex_b, angle, linedef,
                                 sidedef_front, sidedef_back, is_portal,
                                 offset, sector_front, sector_back))

    def extract_subsectors(self) -> None:
        self.subsectors = []
        data = self.entry_data[b'SSECTORS']
        for j in range(len(data)//4):
            sc_u, fs_u = unpack_from('<HH', data, j*4)
            seg_count = Int32(sc_u)
            first_seg = Int32(fs_u)
            # The Map owns the segs; a subsector only points at its slice of
            # them, so the range is collected as pointers rather than sliced
            # (a slice would be a non-owning Span of values).
            segs: list[Ptr[Seg]] = []
            for k in range(first_seg, first_seg + seg_count):
                segs.append(self.segs[k])
            self.subsectors.append(SubSector(segs))

    def extract_bspnodes(self) -> None:
        self.bspnodes = []
        data = self.entry_data[b'NODES']
        for j in range(len(data)//28):
            (px_u, py_u, cpx_u, cpy_u,
             _, _, _,  _, _, _, _, _, rc_u, lc_u) = \
                unpack_from('<hhhhhhhhhhhhhh', data, j*28)
            partition_x = Int32(px_u)
            partition_y = Int32(py_u)
            change_partition_x = Int32(cpx_u)
            change_partition_y = Int32(cpy_u)
            rchild_id = Int32(rc_u)
            lchild_id = Int32(lc_u)
            bspnode = BSPNode(partition_x, partition_y, change_partition_x,
                              change_partition_y, rchild_id, lchild_id)
            self.bspnodes.append(bspnode)

    def extract_things(self) -> None:
        self.things = []
        data = self.entry_data[b'THINGS']
        for j in range(len(data)//10):
            x_u, y_u, angle_u, type_u, _ = unpack_from('<hhhhh', data, j*10)
            x = Int32(x_u)
            y = Int32(y_u)
            angle = Int32(angle_u)
            type_ = Int32(type_u)
            self.things.append(Thing(x, y, angle, type_))


class ClipBufferNode:
    start: Int32
    end: Int32
    occluded: bool
    partitioned: bool
    partitionPoint: Int32
    # A node owns its children, and the type is recursive, so the children need
    # an indirection: Box is the heap-allocated owning container for exactly
    # this shape.
    left: Box[ClipBufferNode] | None
    right: Box[ClipBufferNode] | None

    def __init__(self, start: Int32, end: Int32) -> None:
        self.start = start
        self.end = end
        self.occluded = False
        self.left = None
        self.right = None
        self.partitioned = False
        self.partitionPoint = 0

    def checkSpan(self, start: Int32, end: Int32, result: list[Int32],
                  add: bool) -> None:
        # span completely occluded by node
        if self.occluded and start >= self.start and end <= self.end:
            return

        # no overlap, so node does not apply to span
        if start > self.end or end < self.start:
            return

        # reduce span to overlap with node
        if start <= self.start:
            start = self.start

        if end >= self.end:
            end = self.end

        if add:
            # unpartitioned, unoccluded node covered fully by span
            if (not self.occluded and not self.partitioned and
                    start <= self.start and end >= self.end):
                result.append(start)
                result.append(end)
                self.occluded = True
                return

            # partition if needed
            if not self.partitioned:
                if start == self.start:
                    self.partitionPoint = end
                else:
                    self.partitionPoint = start - 1

                self.left = Box(ClipBufferNode(self.start, self.partitionPoint))
                self.right = Box(ClipBufferNode(self.partitionPoint + 1, self.end))
                self.partitioned = True

        else:
            if not self.partitioned:
                result.append(start)
                result.append(end)
                return

        # Every path reaching here has partitioned the node, so both children
        # exist -- the asserts state that for the compiler, which would
        # otherwise emit a null check per access.
        assert self.left is not None
        assert self.right is not None

        # recurse into left and right
        if start <= self.partitionPoint and end <= self.partitionPoint:
            self.left.checkSpan(start, end, result, add)

        elif start <= self.partitionPoint and end > self.partitionPoint:
            self.left.checkSpan(start, self.partitionPoint, result, add)
            self.right.checkSpan(self.partitionPoint + 1, end, result, add)

        elif start > self.partitionPoint and end > self.partitionPoint:
            self.right.checkSpan(start, end, result, add)

        # left and right occluded, so node fully occluded
        if add and self.left.occluded and self.right.occluded:
            self.occluded = True


def get_special_light(sector: Ptr[Sector], frame_count: Int32) -> Int32:
    special_type = sector.special_type

    if special_type in (1, 17):
        if sector.random[(frame_count & 0xff0) >> 4]:
            return 10
    elif special_type in (2, 12):
        if (frame_count % 120) < 60:
            return 10
    elif special_type in (3, 13):
        if (frame_count % 240) < 120:
            return 10
    elif special_type == 8:
        return OSCILLATION[frame_count & 0xff]

    return 0


def get_wall_colormap(colormaps: readonly[list[Colormap]], currentZ: float,
                      seg: Seg, frame_count: Int32) -> readonly[Colormap]:
    sector = seg.sector_front

    colorMapIndex = Int32((currentZ - 5) * 0.05)
    colorMapIndex = min(colorMapIndex, 32 - (sector.light_level >> 3))

    colorMapIndex += ((((seg.angle + 8192) & 0x7fff) - 16384) & 0x7fff) // 3200
    colorMapIndex += get_special_light(sector, frame_count)

    colorMapIndex = max(min(colorMapIndex, 31), 0)
    return colormaps[colorMapIndex]


def get_flat_colormap(colormaps: readonly[list[Colormap]], currentZ: float,
                      seg: Seg, frame_count: Int32) -> readonly[Colormap]:
    sector = seg.sector_front

    colorMapIndex = Int32((currentZ - 5) * 0.05)
    colorMapIndex = min(colorMapIndex, 32 - (sector.light_level >> 3))

    colorMapIndex += get_special_light(sector, frame_count)

    colorMapIndex = max(min(colorMapIndex, 31), 0)
    return colormaps[colorMapIndex]


def draw_wall_col(drawsurf: bytearray, x: Int32, middleMinY: Int32,
                  middleMaxY: Int32, wallTexture: Ptr[Texture],
                  currentTextureX: float, currentZ: float,
                  middleTextureY: float, middleTextureYStep: float,
                  colormap: readonly[Colormap]) -> None:
    width = wallTexture.width
    height = wallTexture.height
    wallTextureData = wallTexture.data

    tx = Int32(currentTextureX * currentZ) % width
    # tx is fixed for the whole column, so the texture column and the colormap
    # table are looked up once instead of per pixel. Each of those was a
    # bounds-checked index inside the loop.
    column = wallTextureData[tx]
    cdata = colormap.data
    row = middleMinY * WIDTH + x
    for y in range(middleMinY, middleMaxY):
        ty = Int32(middleTextureY) % height
        drawsurf[row] = UInt8(cdata[column[ty]])
        middleTextureY += middleTextureYStep
        row += WIDTH


def draw_flat_col(drawsurf: bytearray, x: Int32, ceilMin: Int32, ceilMax: Int32,
                  seg: Seg, player: Player, flatTexture: list[list[Int32]],
                  flat_h: float, INV: list[float], sign: float,
                  colormaps: readonly[list[Colormap]],
                  frame_count: Int32) -> None:
    # Everything here that does not depend on y is lifted out of the loop. The
    # groupings are kept exactly as the original evaluates them, so the
    # arithmetic is bit-for-bit identical -- only the repetition is removed.
    playerDir = player.direction
    dir_x = playerDir.x
    dir_y = playerDir.y
    player_x = player.x
    player_y = player.y
    zbase = sign * WIDTH_2 * (-flat_h + player.z)
    row = ceilMin * WIDTH + x
    # get_flat_colormap() is inlined here because both of the things it derives
    # from the sector -- the light cap and the special-lighting offset -- are
    # constant for the whole column, so calling it per pixel recomputed them
    # 480k times a frame. The surviving arithmetic is unchanged.
    sector = seg.sector_front
    light_cap = 32 - (sector.light_level >> 3)
    special = get_special_light(sector, frame_count)
    for y in range(ceilMin, ceilMax):
        z = zbase * INV[y]

        colorMapIndex = Int32((z - 5) * 0.05)
        colorMapIndex = min(colorMapIndex, light_cap)
        colorMapIndex += special
        colorMapIndex = max(min(colorMapIndex, 31), 0)
        colormap = colormaps[colorMapIndex]

        px = dir_x * z + player_x
        py = dir_y * z + player_y

        lateralLength = TAN_45_DEG * z

        leftX = -dir_y * lateralLength + px
        leftY = dir_x * lateralLength + py
        rightX = dir_y * lateralLength + px
        rightY = -dir_x * lateralLength + py

        dx = (rightX - leftX) * HEIGHT_INV
        dy = (rightY - leftY) * HEIGHT_INV

        tx = Int32(leftX + dx * x) & 0x3f
        ty = Int32(leftY + dy * x) & 0x3f

        drawsurf[row] = UInt8(colormap.data[flatTexture[tx][ty]])
        row += WIDTH


def draw_sky_col(drawsurf: bytearray, x: Int32, upperMinY: Int32,
                 upperMaxY: Int32, seg: Seg, player: Player) -> None:
    ceil_pic = seg.sector_front.ceil_pic
    # Only called for segs whose ceiling is the sky texture, which resolved.
    assert ceil_pic is not None
    ceilingTextureWidth = ceil_pic.width
    ceilingTextureHeight = ceil_pic.height
    ceilTextureData = ceil_pic.data

    normPlayerAngle = player.angle % (2 * math.pi)
    if normPlayerAngle < 0:
        normPlayerAngle += 2 * math.pi

    textureOffsetX = ceilingTextureWidth * (normPlayerAngle / (math.pi * 0.5))
    dx = ceilingTextureWidth / WIDTH
    dy = ceilingTextureHeight / (WIDTH//2)

    for y in range(upperMinY, upperMaxY):
        tx = Int32(dx * x - textureOffsetX) % ceilingTextureWidth
        ty = Int32(y * dy) % ceilingTextureHeight
        drawsurf[y*WIDTH+x] = UInt8(ceilTextureData[tx][ty])


def draw_seg(seg: Seg, map_: Map, drawsurf: bytearray, scrXA: Int32,
             scrXB: Int32, cbuffer: ClipBufferNode, za: float, zb: float,
             textureX0: float, textureX1: float, frontSidedef: Ptr[Sidedef],
             lowerOcclusion: list[Int32], upperOcclusion: list[Int32],
             frame_count: Int32) -> None:
    # get non-occluded clips from cbuffer
    cbufferResult: list[Int32] = []
    cbuffer.checkSpan(scrXA, scrXB, cbufferResult, not seg.is_portal)

    # no visible clips
    if not cbufferResult:
        return

    player = map_.player
    colormaps = map_.colormaps
    sector_front = seg.sector_front
    sector_back = seg.sector_back

    # front side
    frontCeil = sector_front.ceil_h - player.z
    frontFloor = sector_front.floor_h - player.z
    scrYAFrontCeil = WIDTH_2 * (frontCeil / -za) + HEIGHT_2
    scrYAFrontFloor = WIDTH_2 * (frontFloor / -za) + HEIGHT_2
    scrYBFrontCeil = WIDTH_2 * (frontCeil / -zb) + HEIGHT_2
    scrYBFrontFloor = WIDTH_2 * (frontFloor / -zb) + HEIGHT_2

    # back side
    if seg.is_portal:
        backCeil = sector_back.ceil_h - player.z
        backFloor = sector_back.floor_h - player.z
        scrYABackCeil = WIDTH_2 * (backCeil / -za) + HEIGHT_2
        scrYABackFloor = WIDTH_2 * (backFloor / -za) + HEIGHT_2
        scrYBBackCeil = WIDTH_2 * (backCeil / -zb) + HEIGHT_2
        scrYBBackFloor = WIDTH_2 * (backFloor / -zb) + HEIGHT_2
        hasLowerWall = backFloor > frontFloor
        hasUpperWall = backCeil < frontCeil
    else:
        backCeil = 0
        backFloor = 0
        scrYABackCeil = 0
        scrYABackFloor = 0
        scrYBBackCeil = 0
        scrYBBackFloor = 0
        hasLowerWall = False
        hasUpperWall = False

    # calculate steps
    dxInv = 1.0 / (scrXB - scrXA)
    zInvStep = (1 / zb - 1 / za) * dxInv
    textureXStep = (textureX1 / zb - textureX0 / za) * dxInv
    middleCeilStep = (scrYBFrontCeil - scrYAFrontCeil) * dxInv
    middlefloorStep = (scrYBFrontFloor - scrYAFrontFloor) * dxInv
    lowerCeilStep = (scrYBBackFloor - scrYABackFloor) * dxInv
    lowerfloorStep = (scrYBFrontFloor - scrYAFrontFloor) * dxInv
    upperCeilStep = (scrYBFrontCeil - scrYAFrontCeil) * dxInv
    upperFloorStep = (scrYBBackCeil - scrYABackCeil) * dxInv

    # loop over non-occluded seg clips
    for clip in range(0, len(cbufferResult), 2):
        clipLeft = cbufferResult[clip]
        clipRight = cbufferResult[clip+1]

        currentMiddleCeil = scrYAFrontCeil
        currentMiddleFloor = scrYAFrontFloor

        currentLowerCeil = scrYABackFloor
        currentLowerFloor = scrYAFrontFloor
        currentUpperCeil = scrYAFrontCeil
        currentUpperFloor = scrYABackCeil

        currentZInv = 1 / za
        currentTextureX = textureX0 / za
        scrLeft = scrXA
        scrRight = scrXB

        # narrow to clip
        if scrLeft < clipLeft:
            dif = clipLeft - scrXA
            currentTextureX += dif * textureXStep
            currentZInv += dif * zInvStep
            currentMiddleCeil += dif * middleCeilStep
            currentMiddleFloor += dif * middlefloorStep

            if hasLowerWall:
                currentLowerCeil += dif * lowerCeilStep
                currentLowerFloor += dif * lowerfloorStep

            if hasUpperWall:
                currentUpperCeil += dif * upperCeilStep
                currentUpperFloor += dif * upperFloorStep

            scrLeft = clipLeft

        if scrRight > clipRight:
            scrRight = clipRight

        # draw clip column-wise
        for x in range(scrLeft, scrRight+1):
            currentZ = 1.0 / currentZInv
            colormap = get_wall_colormap(colormaps, currentZ, seg, frame_count)

            middleMaxY = Int32(currentMiddleFloor)
            middleMinY = Int32(currentMiddleCeil)
            middleDy = middleMaxY - middleMinY

            if middleDy == 0:  # on collision with wall
                middleTextureYStep = 0
            else:
                middleTextureYStep = (frontCeil - frontFloor) / middleDy
            middleTextureY = frontSidedef.offset_y

            if middleMinY < lowerOcclusion[x]:
                dif = lowerOcclusion[x] - middleMinY
                middleTextureY = \
                    dif * middleTextureYStep + frontSidedef.offset_y
                middleMinY = lowerOcclusion[x]

            middleMaxY = min(middleMaxY, upperOcclusion[x])

            # middle wall
            middle_texture = frontSidedef.middle_texture
            if not seg.is_portal and middle_texture is not None:
                draw_wall_col(drawsurf, x, middleMinY, middleMaxY,
                              middle_texture, currentTextureX, currentZ,
                              middleTextureY, middleTextureYStep, colormap)

            # floor
            ceilMin = Int32(max(lowerOcclusion[x], middleMaxY))
            if ceilMin < upperOcclusion[x]:
                floor_flat = sector_front.floor_flat.get_data(frame_count)
                draw_flat_col(drawsurf, x, ceilMin, upperOcclusion[x], seg,
                              player, floor_flat, sector_front.floor_h,
                              FLOOR_Y_INV, 1, colormaps, frame_count)
                upperOcclusion[x] = ceilMin

            # lower wall
            if hasLowerWall:
                lowerMaxY = Int32(currentLowerFloor)
                lowerMinY = Int32(currentLowerCeil)

                lowerDy = lowerMaxY - lowerMinY
                lowerTextureYStep = (backFloor - frontFloor) / lowerDy
                lowerTextureY = frontSidedef.offset_y

                if lowerMinY < lowerOcclusion[x]:
                    dif = lowerOcclusion[x] - lowerMinY
                    lowerTextureY = \
                        dif * lowerTextureYStep + frontSidedef.offset_y
                    lowerMinY = lowerOcclusion[x]

                lowerMaxY = min(lowerMaxY, upperOcclusion[x])

                lower_texture = frontSidedef.lower_texture
                if lower_texture is not None:
                    draw_wall_col(drawsurf, x, lowerMinY, lowerMaxY,
                                  lower_texture, currentTextureX, currentZ,
                                  lowerTextureY, lowerTextureYStep,
                                  colormap)

                if lowerMinY < upperOcclusion[x]:
                    upperOcclusion[x] = lowerMinY

                currentLowerCeil += lowerCeilStep
                currentLowerFloor += lowerfloorStep

            # ceil
            ceilMax = Int32(min(upperOcclusion[x], middleMinY))
            if ceilMax > lowerOcclusion[x]:
                # sky
                if sector_front.ceil_pic is not None:
                    draw_sky_col(drawsurf, x, lowerOcclusion[x], ceilMax, seg,
                                 player)
                # ceil
                else:
                    ceil_flat = sector_front.ceil_flat.get_data(frame_count)
                    draw_flat_col(drawsurf, x, lowerOcclusion[x], ceilMax, seg,
                                  player, ceil_flat, sector_front.ceil_h,
                                  CEIL_Y_INV, -1, colormaps, frame_count)

                lowerOcclusion[x] = middleMinY

            # upper wall
            if hasUpperWall:
                upperMaxY = Int32(currentUpperFloor)
                upperMinY = Int32(currentUpperCeil)

                upperDy = upperMaxY - upperMinY
                upperTextureYStep = (frontCeil - backCeil) / upperDy
                upperTextureY = frontSidedef.offset_y

                if upperMinY < lowerOcclusion[x]:
                    dif = lowerOcclusion[x] - upperMinY
                    upperTextureY = \
                        dif * upperTextureYStep + frontSidedef.offset_y
                    upperMinY = lowerOcclusion[x]

                upperMaxY = min(upperMaxY, upperOcclusion[x])
                upper_texture = frontSidedef.upper_texture

                # sky
                if frontSidedef.skyhack or upper_texture is None:
                    if sector_front.ceil_pic is not None:
                        draw_sky_col(drawsurf, x, upperMinY, upperMaxY, seg,
                                     player)
                # wall
                else:
                    draw_wall_col(drawsurf, x, upperMinY, upperMaxY,
                                  upper_texture, currentTextureX, currentZ,
                                  upperTextureY, upperTextureYStep, colormap)

                if upperMaxY > lowerOcclusion[x]:
                    lowerOcclusion[x] = upperMaxY

                currentUpperCeil += upperCeilStep
                currentUpperFloor += upperFloorStep

            currentMiddleCeil += middleCeilStep
            currentMiddleFloor += middlefloorStep
            currentZInv += zInvStep
            currentTextureX += textureXStep


def render(map_: Map, frame_count: Int32) -> Own[bytearray]:
    drawsurf = bytearray(WIDTH * HEIGHT)

    lowerOcclusion: list[Int32] = [0] * WIDTH
    upperOcclusion: list[Int32] = [HEIGHT] * WIDTH

    cbuffer = ClipBufferNode(0, WIDTH-1)

    subsectors: list[Ptr[SubSector]] = []
    map_.bspnodes[-1].visit(map_, subsectors)

    player = map_.player
    player.floor_h = subsectors[0].segs[0].sector_front.floor_h

    for subsector in subsectors:
        if cbuffer.occluded:
            break

        for seg in subsector.segs:
            if cbuffer.occluded:
                break

            # backface/frustrum culling
            pa = seg.vertex_start
            pb = seg.vertex_end
            v0 = Vec2(pa.x - player.x, pa.y - player.y)
            v1 = Vec2(pb.x - player.x, pb.y - player.y)
            v2 = Vec2(player.direction.x, player.direction.y)
            za = v2.dot(v0)
            zb = v2.dot(v1)
            v3 = Vec2(-v2.y, v2.x)
            xa = v3.dot(v0)
            xb = v3.dot(v1)

            if not (za <= 0.1 and zb <= 0.1):
                frontSidedef = seg.sidedef_front
                textureX0 = seg.offset + frontSidedef.offset_x
                textureX1 = seg.offset + seg.length + frontSidedef.offset_x

                if za <= 0.1:
                    p = (zb - 0.1) / (zb - za)
                    xa = xb + p * (xa - xb)
                    textureX0 = textureX1 + p * (textureX0 - textureX1)
                    za = 0.1

                elif zb <= 0.1:
                    p = (za - 0.1) / (za - zb)
                    xb = xa + p * (xb - xa)
                    textureX1 = textureX0 + p * (textureX1 - textureX0)
                    zb = 0.1

                scrXA = Int32(WIDTH_2 * xa / -za) + WIDTH_2
                scrXB = Int32(WIDTH_2 * xb / -zb) + WIDTH_2

                if scrXA < scrXB:
                    draw_seg(seg, map_, drawsurf, scrXA, scrXB, cbuffer, za,
                             zb, textureX0, textureX1, frontSidedef,
                             lowerOcclusion, upperOcclusion, frame_count)

    return drawsurf
