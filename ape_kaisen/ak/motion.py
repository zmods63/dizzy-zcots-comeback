"""Gorilla Tag movement and acting for the apes.

No legs: an ape moves by slamming its hands down and shoving its body past them. Planted
hands press flat on the surface and stay fixed in the world while the body moves. Arms are
never fully straight: every planted hand is kept within MAX_REACH of its shoulder (the body
sinks if it has to) and free hands are pulled inside it. With no hand down the ape sits on
the ground instead of floating.

All measurements are from the user's LAR_Ape rig (metres, rig scale 1) and were checked
against the deformed mesh: palms touch the floor within 0.1 mm at WRIST, the torso rests on
the floor at H_SIT.
Positions are world space; yaw 0 means facing -Y.
"""

import math
import random

from mathutils import Euler, Matrix, Quaternion, Vector

from . import cast as C

ARM_LENGTH = 0.816          # upper arm 0.345 + forearm 0.471
MAX_REACH = 0.88 * ARM_LENGTH
WRIST = 0.0438              # wrist height that puts a flat palm exactly on the surface
H_STAND = 0.32              # standing on both hands: arms at 83% of their length (elbows bent)
H_ONE = 0.17                # one hand down: sink and lean onto it
H_SIT = 0.0112              # no hands down: torso resting on the surface
SPREAD = 0.40               # standing hands' sideways distance from the body centre
SHOULDER = {"L": Vector((0.155, 0.029, 0.331)), "R": Vector((-0.155, 0.029, 0.331))}
UP = Vector((0, 0, 1))


def fwd(yaw):
    return Vector((math.sin(yaw), -math.cos(yaw), 0.0))


def left(yaw):
    return Vector((math.cos(yaw), math.sin(yaw), 0.0))


def yaw_of(d):
    return math.atan2(d.x, -d.y)


def unwrap(a, ref):
    while a - ref > math.pi:
        a -= 2 * math.pi
    while a - ref < -math.pi:
        a += 2 * math.pi
    return a


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def bump(x, center, width):
    return math.exp(-((x - center) / width) ** 2)


def plant_rotation(side, yaw, normal=UP, along=None, splay=0.35):
    """World orientation of a hand pressed flat on a surface: palm into the surface,
    fingers along `along` (default: forward, turned a little outward)."""
    sx = 1 if side == "L" else -1
    n = Vector(normal).normalized()
    if along is None:
        along = fwd(yaw) + left(yaw) * (splay * sx)
    y = (along - n * along.dot(n)).normalized()
    x = -n * sx              # palm side is local +X on the left hand, -X on the right
    z = x.cross(y)
    return Matrix((x, y, z)).transposed().to_euler()


# finger poses: (curl per segment in degrees, spread in degrees); curl + bends toward the palm
FINGER_POSES = {
    "flat": {"index": ((-12, -8, -4), 13), "pinkie": ((-12, -8, -4), -13), "thumb": ((-6, -4, 0), 18)},
    "relaxed": {"index": ((18, 24, 14), 0), "pinkie": ((22, 26, 16), 0), "thumb": ((8, 10, 6), 0)},
    "fist": {"index": ((78, 92, 70), 0), "pinkie": ((80, 92, 70), 0), "thumb": ((28, 40, 30), -8)},
    "open": {"index": ((-4, -2, 0), 16), "pinkie": ((-4, -2, 0), -16), "thumb": ((0, 0, 0), 22)},
    "grip": {"index": ((45, 60, 40), 4), "pinkie": ((48, 60, 40), -4), "thumb": ((20, 25, 15), 10)},
}


class Actor:
    """Animation track for one ape. Keeps the current state so moves chain naturally."""

    def __init__(self, ape, pos, yaw=0.0, ground=0.0):
        self.ape = ape
        self.scale = ape.arm.scale[0]
        self.ground = ground
        self.pos = Vector((pos[0], pos[1], 0))   # point under the body (z unused)
        self.yaw = yaw
        self.hands = {s: self.stand_hand(s) for s in "LR"}
        self._rot = {s: plant_rotation(s, yaw) for s in "LR"}
        self._finger = {"L": None, "R": None}
        self.planted = {"L": True, "R": True}
        self.impacts = []          # (frame, world point, strength) of every hand slam / landing

    # ------------------------------------------------------------ geometry

    def shoulder(self, loc, yaw, pitch=0.0, roll=0.0, side="L"):
        rot = Euler((pitch, roll, yaw), "XYZ").to_matrix()
        return Vector(loc) + rot @ (SHOULDER[side] * self.scale)

    def fit(self, loc, yaw, pitch, roll, hands, planted):
        """Keep arms bent: sink the body until planted hands are within reach, pull free hands in."""
        loc = Vector(loc)
        maxr = MAX_REACH * self.scale
        sink = 0.0
        for s in "LR":
            if planted.get(s):
                d = hands[s] - self.shoulder(loc, yaw, pitch, roll, s)
                if d.length > maxr:
                    horiz = Vector((d.x, d.y, 0)).length
                    if horiz < maxr:
                        sink = max(sink, -d.z - math.sqrt(maxr ** 2 - horiz ** 2))
        loc.z -= max(sink, 0.0)
        out = dict(hands)
        for s in "LR":
            if not planted.get(s):
                sh = self.shoulder(loc, yaw, pitch, roll, s)
                d = out[s] - sh
                if d.length > maxr:
                    out[s] = sh + d.normalized() * maxr
        return loc, out

    def stand_hand(self, side, pos=None, yaw=None, ground=None):
        pos = self.pos if pos is None else pos
        yaw = self.yaw if yaw is None else yaw
        g = self.ground if ground is None else ground
        sx = 1 if side == "L" else -1
        p = Vector((pos.x, pos.y, 0)) + left(yaw) * (SPREAD * sx * self.scale) + fwd(yaw) * (0.16 * self.scale)
        p.z = g + WRIST * self.scale
        return p

    def body_at(self, pos, height=H_STAND, ground=None):
        g = self.ground if ground is None else ground
        return Vector((pos.x, pos.y, g + height * self.scale))

    # ------------------------------------------------------------ low level keys

    def key_body(self, f, loc, yaw, pitch=0.0, roll=0.0):
        arm = self.ape.arm
        arm.location = loc
        arm.rotation_euler = Euler((pitch, roll, yaw), "XYZ")
        arm.keyframe_insert("location", frame=f)
        arm.keyframe_insert("rotation_euler", frame=f)

    def key_hand(self, f, side, p):
        h = self.ape.hand[side]
        h.location = p
        h.keyframe_insert("location", frame=f)

    def key_pose(self, f, loc, yaw, pitch, roll, hands, planted):
        """Body + both hands for one frame, after the reach check."""
        loc, hands = self.fit(loc, yaw, pitch, roll, hands, planted)
        self.key_body(f, loc, yaw, pitch, roll)
        for s in "LR":
            self.key_hand(f, s, hands[s])
        return loc, hands

    def key_plant(self, f, side, amount, rot=None):
        """amount 1 = hand pressed flat in `rot` (a world rotation), 0 = hand follows the arm."""
        if rot is not None:
            rot = rot.copy()
            rot.make_compatible(self._rot[side])
            self._rot[side] = rot
            h = self.ape.hand[side]
            h.rotation_euler = rot
            h.keyframe_insert("rotation_euler", frame=f)
        c = self.ape.pb(f"hand.{side}").constraints["Plant"]
        c.influence = amount
        c.keyframe_insert("influence", frame=f)

    def fingers(self, f, side, pose, force=False):
        if self._finger[side] == pose and not force:
            return
        self._finger[side] = pose
        sign = -1 if side == "L" else 1
        for finger, (curls, spread) in FINGER_POSES[pose].items():
            for seg, curl in zip((1, 2, 3), curls):
                pb = self.ape.pb(f"{finger}{seg}.{side}")
                pb.rotation_quaternion = (Quaternion((1, 0, 0), math.radians(spread if seg == 1 else 0)) @
                                          Quaternion((0, 0, 1), math.radians(curl * sign)))
                pb.keyframe_insert("rotation_quaternion", frame=f)

    def press(self, f, side, p, rot):
        """Hand pressed flat at p."""
        self.key_hand(f, side, p)
        self.key_plant(f, side, 1.0, rot)
        self.fingers(f, side, "flat")
        self.planted[side] = True

    # ------------------------------------------------------------ support

    def support_height(self):
        n = sum(self.planted.values())
        return H_STAND if n == 2 else H_ONE if n == 1 else H_SIT

    def settle(self, f, pitch=None):
        """Key the body at the height its hands can hold up: standing on two hands, sinking
        and leaning onto one, or sitting on the ground with none (never floating)."""
        n = sum(self.planted.values())
        roll = 0.0
        if n == 1:
            roll = -0.14 if self.planted["L"] else 0.14     # lean onto the supporting hand
        if pitch is None:
            pitch = 0.06 if n == 2 else 0.1 if n == 1 else -0.06
        self.key_pose(f, self.body_at(self.pos, self.support_height()), self.yaw, pitch, roll,
                      self.hands, self.planted)

    # ------------------------------------------------------------ standing / idle

    def stand(self, f0, f1, pos=None, yaw=None, breathe=0.01, sway=0.0, hands=None):
        """Stand on both flat hands, breathing. Hands re-plant if pos/yaw changed."""
        if pos is not None:
            self.pos = Vector((pos[0], pos[1], 0))
        if yaw is not None:
            self.yaw = unwrap(yaw, self.yaw)
        for s in "LR":
            self.hands[s] = Vector(hands[s]) if hands else self.stand_hand(s)
            self.press(f0, s, self.hands[s], plant_rotation(s, self.yaw))
        f = f0
        while True:
            t = (f - f0) / 24.0
            bob = breathe * math.sin(t * 2 * math.pi * 0.45) * self.scale
            loc = self.body_at(self.pos) + Vector((0, 0, bob))
            self.key_pose(f, loc, self.yaw, 0.06 + 0.5 * bob, sway * math.sin(t * 2.3), self.hands, self.planted)
            if f >= f1:
                break
            f = min(f + 4, f1)
        for s in "LR":
            self.key_plant(f1, s, 1.0)
        return self

    # ------------------------------------------------------------ locomotion

    def move(self, f0, f1, path, gait="gallop", stride=None, hop=None, lean=None, accel=10, decel=10,
             ground=None, surge=None):
        """Travel along a ground path from f0 to f1.
        'gallop': both hands swing overhead and slam down together, the body is shoved forward
        (speed surges), flies, and glides until the next slam: the classic Gorilla Tag run.
        'walk': hands alternate, the body sways and pushes off each hand."""
        g = self.ground if ground is None else ground
        pts = [Vector((p[0], p[1], 0)) for p in [self.pos] + list(path)]
        seg = [(b - a).length for a, b in zip(pts, pts[1:])]
        total = sum(seg)
        if total < 1e-4:
            return self.stand(f0, f1)
        sc = self.scale
        walk = gait == "walk"
        stride = (stride or (0.9 if walk else 1.9)) * sc
        hop = (hop if hop is not None else (0.025 if walk else 0.26)) * sc
        lean = lean if lean is not None else (0.1 if walk else 0.26)
        surge = surge if surge is not None else (0.15 if walk else 0.42)
        contact = 0.5 if walk else 0.32
        reach = (0.28 if walk else 0.40) * sc

        def point(s):
            s = min(max(s, 0.0), total)
            for a, b, L in zip(pts, pts[1:], seg):
                if s <= L:
                    return a + (b - a) * (s / L if L else 0), (b - a).normalized() if L else fwd(self.yaw)
                s -= L
            return pts[-1], (pts[-1] - pts[-2]).normalized()

        n = f1 - f0
        weights = [min(1.0, (i + 0.5) / max(accel, 1), (n - i - 0.5) / max(decel, 1)) for i in range(n)]
        wsum = sum(weights)
        prog = [0.0]
        for w in weights:
            prog.append(prog[-1] + w / wsum)
        cycles = max(1, round(total / stride))
        stride_real = total / cycles
        offsets = {"L": 0.0, "R": 0.5} if walk else {"L": 0.0, "R": 0.03}

        def warp(pc):
            """Distance covered within a cycle: fast right after the shove, gliding before the next."""
            return pc + surge * (math.sin(2 * math.pi * (pc - contact)) + math.sin(2 * math.pi * contact)) / (2 * math.pi)

        def plant(side, k):
            p, d = point((k + offsets[side]) * stride_real + reach)
            sx = 1 if side == "L" else -1
            q = p + left(yaw_of(d)) * (SPREAD * 0.85 * sx * sc)
            q.z = g + WRIST * sc
            return q, plant_rotation(side, yaw_of(d))

        end_yaw = yaw_of(point(total)[1])
        final = {s: (self.stand_hand(s, pos=pts[-1], yaw=end_yaw, ground=g), plant_rotation(s, end_yaw))
                 for s in "LR"}
        start_yaw, yaw = self.yaw, self.yaw
        slammed = {"L": -1, "R": -1}
        for i in range(n + 1):
            f = f0 + i
            phase_t = prog[i] * cycles
            k_t = min(math.floor(phase_t), cycles)
            pc = phase_t - k_t if k_t < cycles else 0.0
            s = stride_real * (k_t + warp(pc)) if k_t < cycles else total
            p, d = point(s)
            target_yaw = unwrap(yaw_of(d), yaw)
            yaw = start_yaw + (unwrap(target_yaw, start_yaw) - start_yaw) * smooth(i / 6) if i < 6 else target_yaw
            speed = min((prog[min(i + 1, n)] - prog[max(i - 1, 0)]) / 2 * n, 1.5)
            effort = min(speed, 1.0)
            if walk:
                h = hop * abs(math.sin(math.pi * 2 * pc)) - 0.02 * sc * bump(pc % 0.5, 0.05, 0.08)
                roll = 0.07 * math.sin(math.pi * 2 * pc) * effort
                pitch = 0.06 + lean * effort
            else:
                h = -0.07 * sc * math.sin(math.pi * pc / contact) if pc < contact else \
                    hop * math.sin(math.pi * (pc - contact) / (1 - contact))
                roll = 0.0
                pitch = 0.06 + (lean + 0.12 * bump(pc, 0.06, 0.1) - 0.09 * bump(pc, contact, 0.1)) * effort
            body = Vector((p.x, p.y, g + H_STAND * sc + h * effort))

            hands, planted = {}, {}
            for side in "LR":
                hp = phase_t - offsets[side]
                k = math.floor(hp)
                local = hp - k
                last = k + 1 > cycles
                if hp < 0:
                    q, rot = plant(side, 0)
                    hands[side] = self.hands[side].lerp(q, smooth(phase_t / max(offsets[side], 1e-3)))
                    planted[side] = True
                    self.key_plant(f, side, 1.0, rot)
                elif local < contact or k >= cycles:
                    q, rot = final[side] if k >= cycles else plant(side, k)
                    hands[side], planted[side] = q, True
                    self.key_plant(f, side, 1.0, rot)
                    self.fingers(f, side, "flat")
                    if slammed[side] != k:
                        slammed[side] = k
                        self.impacts.append((f, q.copy(), (0.4 if walk else 1.0) * effort))
                else:
                    a, _ = plant(side, k)
                    b, rot_b = final[side] if last else plant(side, k + 1)
                    u = (local - contact) / (1 - contact)
                    sx = 1 if side == "L" else -1
                    along = a.lerp(b, smooth(min(u / 0.82, 1.0)))
                    lift = (0.12 if walk else 0.72) * sc * math.sin(math.pi * u) ** 0.55 * effort
                    flare = left(yaw) * (sx * (0.02 if walk else 0.12) * sc * math.sin(math.pi * u))
                    ahead = fwd(yaw) * ((0.08 if walk else 0.26) * sc * math.sin(math.pi * u))
                    hands[side] = along + Vector((0, 0, lift)) + flare + ahead
                    planted[side] = False
                    self.key_plant(f, side, max(0.0, (u - 0.85) / 0.15), rot_b)   # palm peels off at once
                    self.fingers(f, side, "relaxed" if 0.12 < u < 0.86 else "flat")
            self.key_pose(f, body, yaw, pitch, roll, hands, planted)
            if i % 2 == 0 or i == n:
                nod = 6.0 * bump(pc, 0.06, 0.12) - 5.0 * bump(pc, contact + 0.15, 0.15) if not walk else 0.0
                self.head(f, 0.0, (pitch * 57.3) * 0.6 - nod)
        self.pos, self.yaw = pts[-1], yaw
        self.hands = {s: final[s][0] for s in "LR"}
        for s in "LR":
            self.press(f1, s, final[s][0], final[s][1])
        self.head(f1 + 6, 0.0, 0.0)
        return self

    # ------------------------------------------------------------ jumps

    def jump(self, f0, f1, target, apex=1.2, target_ground=None, crouch=6, land=8, spin=0.0):
        """Wind up (body sinks, hands press), explode off both hands, fly, slam down and absorb."""
        g0 = self.ground
        g1 = g0 if target_ground is None else target_ground
        sc = self.scale
        start = Vector(self.pos)
        end = Vector((target[0], target[1], 0))
        d = end - start
        yaw = unwrap(yaw_of(d), self.yaw) if d.length > 0.05 else self.yaw
        launch, touch = f0 + crouch, f1 - land
        b0, b1 = self.body_at(start, ground=g0), self.body_at(end, ground=g1)
        low = 0.15 * sc
        top = max(b0.z, b1.z) + apex * sc
        push = {s: self.stand_hand(s, pos=start, yaw=yaw, ground=g0) for s in "LR"}
        for f in range(f0, launch + 1):
            t = smooth((f - f0) / max(crouch, 1))
            hands = {s: self.hands[s].lerp(push[s], t) for s in "LR"}
            for s in "LR":
                self.press(f, s, hands[s], plant_rotation(s, yaw))
            self.key_pose(f, b0 - Vector((0, 0, low * t)), self.yaw + (yaw - self.yaw) * t,
                          0.06 + 0.32 * t, 0.0, hands, {"L": True, "R": True})
        self.impacts.append((launch, start.lerp(end, 0.0) + Vector((0, 0, g0)), 0.8))
        land_p = {s: self.stand_hand(s, pos=end, yaw=yaw, ground=g1) + fwd(yaw) * (0.1 * sc) for s in "LR"}
        n = touch - launch
        for i in range(1, n + 1):
            u = i / n
            xy = start.lerp(end, u)
            z = (1 - u) ** 2 * (b0.z - low) + 2 * (1 - u) * u * (2 * top - 0.5 * (b0.z - low + b1.z)) + u ** 2 * b1.z
            f = launch + i
            body = Vector((xy.x, xy.y, z))
            pitch = 0.38 - 0.6 * u + spin * u
            hands, planted = {}, {}
            for s in "LR":
                sx = 1 if s == "L" else -1
                if u < 0.1:
                    hands[s], planted[s] = push[s], True
                    self.key_plant(f, s, 1.0 - u / 0.1)
                    continue
                up = Vector((0, 0, 0.45 * sc * math.sin(math.pi * min(u * 1.4, 1.0)))) if u < 0.7 else Vector()
                swing = body + left(yaw) * (0.5 * sx * sc) + fwd(yaw) * (0.28 * sc) + up
                hands[s] = swing.lerp(land_p[s], smooth((u - 0.55) / 0.45)) if u > 0.55 else swing
                planted[s] = False
                self.key_plant(f, s, smooth((u - 0.82) / 0.18), plant_rotation(s, yaw))
                self.fingers(f, s, "open" if u < 0.82 else "flat")
            self.key_pose(f, body, yaw, pitch, 0.0, hands, planted)
        self.pos, self.yaw, self.ground = end, yaw, g1
        self.impacts.append((touch, end + Vector((0, 0, g1)), 1.2))
        for f in range(touch + 1, f1 + 1):
            t = (f - touch) / max(land, 1)
            dip = 0.16 * sc * math.sin(math.pi * min(t * 1.4, 1.0)) * (1 - t * 0.3)
            for s in "LR":
                self.press(f, s, land_p[s], plant_rotation(s, yaw))
            self.key_pose(f, b1 - Vector((0, 0, dip)), yaw, 0.06 + 0.28 * (1 - smooth(t)), 0.0,
                          land_p, {"L": True, "R": True})
        self.hands = dict(land_p)
        return self

    # ------------------------------------------------------------ climbing

    def climb(self, f0, f1, wall_point, wall_normal, top_z, pulls=None, gap=0.36):
        """Climb a vertical wall hand over hand; palms slap flat against the wall."""
        nrm = Vector(wall_normal).normalized()
        sc = self.scale
        yaw = unwrap(yaw_of(-nrm), self.yaw)
        base = Vector(wall_point)
        z0 = self.ground + H_STAND * sc
        rise = top_z - z0
        pulls = pulls or max(2, round(rise / (0.5 * sc)))
        frames = f1 - f0
        side_vec = left(yaw)
        for i in range(frames + 1):
            f = f0 + i
            u = i / frames
            phase = u * pulls
            k = math.floor(phase)
            pc = phase - k
            surge_t = smooth(min(pc / 0.55, 1.0))
            z = z0 + rise * (min(k, pulls) + surge_t) / pulls if k < pulls else top_z
            body = base + nrm * (gap * sc)
            body.z = z
            hands, planted = {}, {}
            for side in "LR":
                sx = 1 if side == "L" else -1
                own = (k % 2 == 0) == (side == "L")
                hz_now = z0 + rise * (k + (1 if own else 0.5)) / pulls + 0.42 * sc
                hz_next = z0 + rise * (k + 2 if own else k + 1.5) / pulls + 0.42 * sc
                moving = own and pc >= 0.55
                t = smooth((pc - 0.55) / 0.45) if moving else 0.0
                hp = base + nrm * (WRIST * sc + 0.1 * sc * math.sin(math.pi * t)) + side_vec * (0.28 * sx * sc)
                hp.z = min(hz_now + (hz_next - hz_now) * t, top_z + 0.35 * sc)
                hands[side], planted[side] = hp, not moving
                self.key_plant(f, side, 0.2 if moving else 1.0,
                               plant_rotation(side, yaw, normal=nrm, along=UP + side_vec * (0.3 * sx)))
                self.fingers(f, side, "relaxed" if moving else "flat")
                if own and abs(pc - 0.0) < 1.0 / frames * pulls and k > 0:
                    self.impacts.append((f, hp.copy(), 0.5))
            self.key_pose(f, body + side_vec * (0.04 * sc * math.sin(math.pi * phase)), yaw, -0.1,
                          0.07 * math.sin(math.pi * phase), hands, {s: False for s in "LR"})
        self.yaw = yaw
        self.pos = Vector((base.x, base.y, 0)) + nrm * (gap * sc)
        return self

    # ------------------------------------------------------------ gestures and face

    def hand_to(self, f, side, p, pose=None, plant=0.0, rot=None, settle=True):
        """Key a hand at a world point (gestures, punches, grabs). The hand leaves the ground, so
        the body settles to what the remaining hands can hold up (see settle)."""
        self.hands[side] = Vector(p)
        self.planted[side] = plant >= 0.5
        self.key_plant(f, side, plant, rot)
        if pose:
            self.fingers(f, side, pose)
        if settle:
            self.settle(f)
        else:
            self.key_hand(f, side, self.hands[side])

    def plant_hand(self, f, side, p=None, settle=True):
        """Put a hand back down flat (at p, or its normal standing spot)."""
        p = self.stand_hand(side) if p is None else Vector(p)
        self.hands[side] = p
        self.press(f, side, p, plant_rotation(side, self.yaw))
        self.impacts.append((f, p.copy(), 0.3))
        if settle:
            self.settle(f)

    def hold_pose(self, f):
        """Re-key everything as it is (to hold a pose until f)."""
        self.settle(f)

    def body_to(self, f, pos=None, yaw=None, height=None, pitch=0.06, roll=0.0, ground=None):
        if pos is not None:
            self.pos = Vector((pos[0], pos[1], 0))
        if yaw is not None:
            self.yaw = unwrap(yaw, self.yaw)
        if ground is not None:
            self.ground = ground
        h = self.support_height() if height is None else height
        self.key_pose(f, self.body_at(self.pos, h), self.yaw, pitch, roll, self.hands, self.planted)

    def local(self, x, y, z, pos=None, yaw=None, height=None):
        """Point in the ape's own frame (x left, y forward, z up) from its body origin."""
        pos = self.pos if pos is None else pos
        yaw = self.yaw if yaw is None else yaw
        base = self.body_at(pos, self.support_height() if height is None else height)
        return base + left(yaw) * (x * self.scale) + fwd(yaw) * (y * self.scale) + Vector((0, 0, z * self.scale))

    def head(self, f, yaw=0.0, pitch=0.0, roll=0.0):
        """Turn the head (degrees). yaw +: toward the ape's left; pitch +: look up."""
        for name, share in (("Bone.001", 0.35), ("head", 0.65)):
            pb = self.ape.pb(name)
            pb.rotation_quaternion = (Quaternion((0, 1, 0), math.radians(yaw) * share) @
                                      Quaternion((1, 0, 0), math.radians(-pitch) * share) @
                                      Quaternion((0, 0, 1), math.radians(roll) * share))
            pb.keyframe_insert("rotation_quaternion", frame=f)

    def shape(self, f, name, value, eyes_too=True):
        kb = self.ape.shape_body.get(name)
        if kb:
            kb.value = value
            kb.keyframe_insert("value", frame=f)
        if eyes_too:
            ke = self.ape.shape_eyes.get(name)
            if ke:
                ke.value = value
                ke.keyframe_insert("value", frame=f)

    def blink(self, f, hold=0):
        self.shape(f - 1, "EyeBlink", 0.0, eyes_too=False)
        self.shape(f + 1, "EyeBlink", 1.0, eyes_too=False)
        self.shape(f + 2 + hold, "EyeBlink", 1.0, eyes_too=False)
        self.shape(f + 4 + hold, "EyeBlink", 0.0, eyes_too=False)

    def eyelids(self, f, amount):
        """0 open .. 1 closed; ~0.3 is a squint (angry / determined)."""
        self.shape(f, "EyeBlink", amount, eyes_too=False)

    def talk(self, f0, f1, loud=0.6, rate=3.2, seed=0):
        """Mouth flaps for a line of dialogue."""
        rnd = random.Random(seed + f0)
        self.shape(f0 - 1, "MouthOpen", 0.0)
        f = f0
        while f < f1 - 2:
            self.shape(f, "MouthOpen", loud * rnd.uniform(0.45, 1.0))
            f += max(2, int(24 / (rate * 2)))
            self.shape(f, "MouthOpen", loud * rnd.uniform(0.0, 0.2))
            f += max(2, int(24 / (rate * 2)) + rnd.randint(-1, 1))
        self.shape(f1, "MouthOpen", 0.0)
