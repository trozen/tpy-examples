from random import random, seed
from math import sqrt, inf
import sys
import time
from typing import Final, Protocol
from tpy import Int32, Own, Ptr, copy, dynamic
from tplib import Box

# path tracer, (c) jonas wagner (http://29a.ch/)
# http://29a.ch/2010/5/17/path-tracing-a-cornell-box-in-javascript
# converted to Python by <anonymous>

ITERATIONS: Final[Int32] = 10  # should be much higher for good quality


class V3:
    x: float
    y: float
    z: float

    def __init__(self, x_: float, y_: float, z_: float) -> None:
        self.x = x_
        self.y = y_
        self.z = z_

    def add(self, v: V3) -> Own[V3]:
        return V3(self.x + v.x, self.y + v.y, self.z + v.z)

    def iadd(self, v: V3) -> None:
        self.x += v.x
        self.y += v.y
        self.z += v.z

    def sub(self, v: V3) -> Own[V3]:
        return V3(self.x - v.x, self.y - v.y, self.z - v.z)

    def subdot(self, v: V3, u: V3) -> float:
        return (self.x - v.x) * u.x + (self.y - v.y) * u.y + (self.z - v.z) * u.z

    def subdot2(self, v: V3) -> float:
        return (self.x - v.x) ** 2 + (self.y - v.y) ** 2 + (self.z - v.z) ** 2

    def mul(self, v: V3) -> Own[V3]:
        return V3(self.x * v.x, self.y * v.y, self.z * v.z)

#    def div(self, v):
#        return V3(self.x / v.x, self.y / v.y, self.z / v.z)

    def muls(self, s: float) -> Own[V3]:
        return V3(self.x * s, self.y * s, self.z * s)

    def divs(self, s: float) -> Own[V3]:
        return self.muls(1.0 / s)

    def dot(self, v: V3) -> float:
        return self.x * v.x + self.y * v.y + self.z * v.z

    def normalize(self) -> Own[V3]:
        return self.divs(sqrt(self.dot(self)))


def getRandomNormalInHemisphere(v: V3) -> Own[V3]:
    """
    This is my crude way of generating random normals in a hemisphere.
    In the first step I generate random vectors with components
    from -1 to 1. As this introduces a bias I discard all the points
    outside of the unit sphere. Now I've got a random normal vector.
    The last step is to mirror the poif it is in the wrong hemisphere.
    """
    v2 = V3(0.0, 0.0, 0.0)
    v2_dot = 0.0
    while True:
        # The three draws are hoisted out of the V3(...) call because
        # TurboPython evaluates call arguments right-to-left; inline, they
        # would consume the random stream backwards (see README).
        r0 = random() * 2.0 - 1.0
        r1 = random() * 2.0 - 1.0
        r2 = random() * 2.0 - 1.0
        v2 = V3(r0, r1, r2)
        v2_dot = v2.dot(v2)
        if v2_dot <= 1.0:
            break

    # should only require about 1.9 iterations of average
    # v2 = v2.normalize()
    v2 = v2.divs(sqrt(v2_dot))

    # if the pois in the wrong hemisphere, mirror it
    if v2.dot(v) < 0.0:
        return v2.muls(-1.0)
    return v2


class Ray:
    origin: V3
    direction: V3

    def __init__(self, origin: V3, direction: V3) -> None:
        self.origin = copy(origin)
        self.direction = copy(direction)


class Camera:
    """
    The camera is defined by an eyepo(origin) and three corners
    of the view plane (it's a rect in my case...)
    """

    origin: V3
    topleft: V3
    topright: V3
    bottomleft: V3
    xd: V3
    yd: V3

    def __init__(self, origin: V3, topleft: V3, topright: V3, bottomleft: V3) -> None:
        self.origin = copy(origin)
        self.topleft = copy(topleft)
        self.topright = copy(topleft)
        self.bottomleft = copy(bottomleft)

        self.xd = topright.sub(topleft)
        self.yd = bottomleft.sub(topleft)

    def getRay(self, x: float, y: float) -> Own[Ray]:
        # poon screen plane
        p = self.topleft.add(self.xd.muls(x)).add(self.yd.muls(y))
        return Ray(self.origin, p.sub(self.origin).normalize())


class Sphere:
    center: V3
    radius: float
    radius2: float

    def __init__(self, center: V3, radius: float) -> None:
        self.center = copy(center)
        self.radius = radius
        self.radius2 = radius * radius

    # returns distance when ray intersects with sphere surface
    def intersect(self, ray: Ray) -> float:
        b = ray.origin.subdot(self.center, ray.direction)
        c = ray.origin.subdot2(self.center) - self.radius2
        d = b * b - c
        return (-b - sqrt(d)) if d > 0 else -1.0

    def getNormal(self, point: V3) -> Own[V3]:
        return point.sub(self.center).normalize()


@dynamic
class Surface(Protocol):
    """The one method subclasses override -- see README."""

    def bounce(self, ray: Ray, normal: V3) -> Own[V3]:
        ...


class Material(Surface):
    color: V3
    emission: V3

    def __init__(self, color: V3, emission: V3 | None = None) -> None:
        self.color = copy(color)
        self.emission = V3(0.0, 0.0, 0.0) if emission is None else emission

    def bounce(self, ray: Ray, normal: V3) -> Own[V3]:
        return getRandomNormalInHemisphere(normal)


class Chrome(Material):
    def __init__(self, color: V3) -> None:
        super().__init__(color)

    def bounce(self, ray: Ray, normal: V3) -> Own[V3]:
        theta1 = abs(ray.direction.dot(normal))
        return ray.direction.add(normal.muls(theta1 * 2.0))


class Glass(Material):
    ior: float
    reflection: float

    def __init__(self, color: V3, ior: float, reflection: float) -> None:
        super().__init__(color)
        self.ior = ior
        self.reflection = reflection

    def bounce(self, ray: Ray, normal: V3) -> Own[V3]:
        theta1 = abs(ray.direction.dot(normal))
        if theta1 >= 0.0:
            internalIndex = self.ior
            externalIndex = 1.0
        else:
            internalIndex = 1.0
            externalIndex = self.ior
        eta = externalIndex / internalIndex
        theta2 = sqrt(1.0 - (eta * eta) * (1.0 - (theta1 * theta1)))
        rs = (externalIndex * theta1 - internalIndex * theta2) / (
            externalIndex * theta1 + internalIndex * theta2
        )
        rp = (internalIndex * theta1 - externalIndex * theta2) / (
            internalIndex * theta1 + externalIndex * theta2
        )
        reflectance = rs * rs + rp * rp
        # reflection
        if random() < reflectance + self.reflection:
            return ray.direction.add(normal.muls(theta1 * 2.0))
        # refraction
        return (
            ray.direction.add(normal.muls(theta1)).muls(eta).add(normal.muls(-theta2))
        )


class Body:
    shape: Sphere
    material: Box[Material]

    def __init__(self, shape: Sphere, material: Own[Box[Material]]) -> None:
        self.shape = copy(shape)
        self.material = material


class Output:
    width: Int32
    height: Int32

    def __init__(self, width: Int32, height: Int32) -> None:
        self.width = width
        self.height = height


class Scene:
    output: Output
    camera: Camera
    objects: list[Body]

    def __init__(
        self, output: Output, camera: Camera, objects: Own[list[Body]]
    ) -> None:
        self.output = copy(output)
        self.camera = copy(camera)
        self.objects = objects


class Renderer:
    scene: Scene
    buffer: list[V3]

    def __init__(self, scene: Own[Scene]) -> None:
        self.scene = scene
        self.buffer = [
            V3(0.0, 0.0, 0.0)
            for i in range(self.scene.output.width * self.scene.output.height)
        ]

#    def clearBuffer(self):
#        for i in range(len(self.buffer)):
#            self.buffer[i].x = 0.0
#            self.buffer[i].y = 0.0
#            self.buffer[i].z = 0.0

    def iterate(self) -> None:
        w = self.scene.output.width
        h = self.scene.output.height
        i = 0
        # randomly jitter pixels so there is no aliasing
        y = random() / h
        ystep = 1.0 / h
        while y < 0.99999:
            x = random() / w
            xstep = 1.0 / w
            while x < 0.99999:
                ray = self.scene.camera.getRay(x, y)
                color = self.trace(ray, 0)
                self.buffer[i].iadd(color)
                i += 1
                x += xstep
            y += ystep

    def trace(self, ray: Ray, n: Int32) -> Own[V3]:
        mint = inf

        # trace no more than 5 bounces
        if n > 4:
            return V3(0.0, 0.0, 0.0)

        hit: Ptr[Body] = None

        for i in range(len(self.scene.objects)):
            o: Ptr[Body] = self.scene.objects[i]
            t = o.shape.intersect(ray)
            if t > 0 and t <= mint:
                mint = t
                hit = o

        if hit is None:
            return V3(0.0, 0.0, 0.0)

        point = ray.origin.add(ray.direction.muls(mint))
        normal = hit.shape.getNormal(point)
        direction = hit.material.bounce(ray, normal)
        # if the ray is refractedmove the intersection poa bit in
        if direction.dot(ray.direction) > 0.0:
            point = ray.origin.add(ray.direction.muls(mint * 1.0000001))
            # otherwise move it out to prevent problems with floating point
            # accuracy
        else:
            point = ray.origin.add(ray.direction.muls(mint * 0.9999999))
        newray = Ray(point, direction)
        return (
            self.trace(newray, n + 1).mul(hit.material.color).add(hit.material.emission)
        )

    @staticmethod
    def cmap(x: float) -> Int32:
        return 0 if x < 0.0 else (255 if x > 1.0 else Int32(x * 255))

    # / Write image to PPM file
    def saveFrame(self, filename: str, nframe: Int32) -> None:
        fout = open(filename, "w")
        fout.write(f"P3\n{self.scene.output.width} {self.scene.output.height}\n255\n")
        for p in self.buffer:
            fout.write(
                f"{Renderer.cmap(p.x / nframe)} "
                f"{Renderer.cmap(p.y / nframe)} "
                f"{Renderer.cmap(p.z / nframe)}\n"
            )
        fout.close()


def main(iterations: Int32) -> None:
    width = 320
    height = 240

    scene = Scene(
        Output(width, height),
        Camera(
            V3(0.0, -0.5, 0.0),
            V3(-1.3, 1.0, 1.0),
            V3(1.3, 1.0, 1.0),
            V3(-1.3, 1.0, -1.0),
        ),
        [
            # glowing sphere
            # Body(Sphere(V3(0.0, 3.0, 0.0), 0.5), Box(Material(V3(0.9, 0.9, 0.9), V3(1.5, 1.5, 1.5)))),
            # glass sphere
            Body(
                Sphere(V3(1.0, 2.0, 0.0), 0.5),
                Box(Glass(V3(1.00, 1.00, 1.00), 1.5, 0.1)),
            ),
            # chrome sphere
            Body(Sphere(V3(-1.1, 2.8, 0.0), 0.5), Box(Chrome(V3(0.8, 0.8, 0.8)))),
            # floor
            Body(
                Sphere(V3(0.0, 3.5, -10e6), 10e6 - 0.5),
                Box(Material(V3(0.9, 0.9, 0.9))),
            ),
            # back
            Body(Sphere(V3(0.0, 10e6, 0.0), 10e6 - 4.5), Box(Material(V3(0.9, 0.9, 0.9)))),
            # left
            Body(Sphere(V3(-10e6, 3.5, 0.0), 10e6 - 1.9), Box(Material(V3(0.9, 0.5, 0.5)))),
            # right
            Body(Sphere(V3(10e6, 3.5, 0.0), 10e6 - 1.9), Box(Material(V3(0.5, 0.5, 0.9)))),
            # top light, the emmision should be close to that of warm sunlight (~5400k)
            Body(
                Sphere(V3(0.0, 0.0, 10e6), 10e6 - 2.5),
                Box(Material(V3(0.0, 0.0, 0.0), V3(1.6, 1.47, 1.29))),
            ),
            # front
            Body(
                Sphere(V3(0.0, -10e6, 0.0), 10e6 - 2.5),
                Box(Material(V3(0.9, 0.9, 0.9))),
            ),
        ],
    )

    renderer = Renderer(scene)

    nframe = 0
    for count in range(iterations):
        renderer.iterate()
        sys.stdout.write("*")
        sys.stdout.flush()
        nframe += 1

    renderer.saveFrame("pt.ppm", nframe)


if __name__ == '__main__':
    # path_tracing.py [samples-per-pixel]
    argv = sys.argv[1:]
    if len(argv) > 0:
        # one render at the requested quality, instead of the timing loop
        t0 = time.time()
        seed(0)
        main(Int32(int(argv[0])))
        print()
        print(f'TIME {time.time()-t0:.2f}')
    else:
        t0 = time.time()
        for n in range(10):
            if n == 5:
                t0 = time.time()  # pypy has stabilized
            seed(n)
            main(ITERATIONS)
            print()
        print(f'TIME {time.time()-t0:.2f}')
