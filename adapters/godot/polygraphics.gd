## PolyGraphics → Godot 4 adapter. Drop this single file into a Godot project.
##
## Consumes compiled IR (out/compiled/*.json):
##   var ir := PolyGraphics.load_ir("res://assets/pg/enemy-imp.json")
##   var node := PolyGraphics.build(ir)                # Node2D tree, parts addressable
##   add_child(node)
##   var tweens := PolyGraphics.play(node, ir, "idle") # data-driven animation
##
## Each top-level IR node becomes a Node2D (meta "pg_id" = part id) holding
## Polygon2D / Line2D children. Colors arrive as [r,g,b,a] floats — no token
## logic lives here. Gradients render as their flat mid-color fallback.
## Mirrored copies carry meta "pg_sign" = -1 so x/rot animation offsets stay
## symmetric. `play` requires the node to be inside the scene tree.
class_name PolyGraphics
extends RefCounted

const SEGS := 48


static func load_ir(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("polygraphics: cannot open %s" % path)
		return {}
	var data: Variant = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY or data.get("format", "") != "polygraphics-ir":
		push_error("polygraphics: %s is not polygraphics-ir" % path)
		return {}
	return data


static func build(ir: Dictionary, variant: String = "") -> Node2D:
	var nodes: Array = ir["nodes"]
	var vscale := 1.0
	if variant != "":
		var v: Dictionary = ir["variants"].get(variant, {})
		if v.is_empty():
			push_error("polygraphics: asset %s has no variant %s" % [ir["id"], variant])
		else:
			nodes = v["nodes"]
			vscale = v["scale"]
	var root := Node2D.new()
	root.name = String(ir["id"]).replace(".", "_")
	root.scale = Vector2(vscale, vscale)
	for n: Dictionary in nodes:
		root.add_child(_build_node(n, true))
	return root


static func _build_node(n: Dictionary, top_level: bool) -> Node2D:
	var node := Node2D.new()
	node.name = String(n["id"])
	node.position = _vec(n["at"])
	node.rotation_degrees = n["rot"]
	node.scale = _vec(n["scale"])
	if n["opacity"] < 1.0:
		node.modulate.a = n["opacity"]
	if top_level:
		node.set_meta("pg_id", String(n["id"]))
		node.set_meta("pg_sign", -1.0 if n["scale"][0] < 0.0 else 1.0)
		node.set_meta("pg_base_pos", _vec(n["at"]))
		node.set_meta("pg_base_rot", float(n["rot"]))
		node.set_meta("pg_base_scale", _vec(n["scale"]))
		node.set_meta("pg_base_alpha", node.modulate.a)
	for d: Dictionary in n["draws"]:
		_add_draw(node, d)
	for c: Dictionary in n["children"]:
		node.add_child(_build_node(c, false))
	return node


static func _add_draw(parent: Node2D, d: Dictionary) -> void:
	var op: String = d["op"]
	if op == "ringarc":
		var line := Line2D.new()
		line.points = _arc_pts(d["r"], d["from"], d["to"], SEGS)
		line.width = d["width"]
		line.default_color = _color(d.get("fill", [1, 0, 1, 1]))
		line.closed = absf(float(d["to"]) - float(d["from"])) >= 360.0
		line.joint_mode = Line2D.LINE_JOINT_ROUND
		line.begin_cap_mode = Line2D.LINE_CAP_ROUND
		line.end_cap_mode = Line2D.LINE_CAP_ROUND
		line.antialiased = true
		parent.add_child(line)
		return
	var pts := _outline(d)
	if d.has("fill"):
		var poly := Polygon2D.new()
		poly.polygon = pts
		poly.color = _color(d["fill"])
		poly.antialiased = true
		parent.add_child(poly)
	if d.has("stroke"):
		var stroke: Dictionary = d["stroke"]
		var line := Line2D.new()
		line.points = pts
		line.closed = true
		line.width = stroke["width"]
		line.default_color = _color(stroke["color"])
		line.joint_mode = Line2D.LINE_JOINT_ROUND
		line.antialiased = true
		parent.add_child(line)


static func _outline(d: Dictionary) -> PackedVector2Array:
	match String(d["op"]):
		"disc":
			return _ellipse_pts(d["r"], d["r"])
		"ellipse":
			return _ellipse_pts(d["rx"], d["ry"])
		"rect":
			return _rounded_rect_pts(d["w"], d["h"], d["corner"])
		"polygon":
			var out := PackedVector2Array()
			for p: Array in d["points"]:
				out.append(_vec(p))
			return out
		"wedge":
			var fan := PackedVector2Array([Vector2.ZERO])
			fan.append_array(_arc_pts(d["r"], d["from"], d["to"], 24))
			return fan
	return PackedVector2Array()


static func _ellipse_pts(rx: float, ry: float) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in SEGS:
		var a := TAU * i / SEGS
		out.append(Vector2(rx * cos(a), ry * sin(a)))
	return out


static func _arc_pts(r: float, from_deg: float, to_deg: float, segs: int) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in segs + 1:
		var a := deg_to_rad(from_deg + (to_deg - from_deg) * i / segs)
		out.append(Vector2(r * cos(a), r * sin(a)))
	return out


static func _rounded_rect_pts(w: float, h: float, corner: float) -> PackedVector2Array:
	var c: float = minf(corner, minf(w / 2.0, h / 2.0))
	if c <= 0.0:
		return PackedVector2Array([
			Vector2(-w / 2, -h / 2), Vector2(w / 2, -h / 2),
			Vector2(w / 2, h / 2), Vector2(-w / 2, h / 2),
		])
	var out := PackedVector2Array()
	var corners := [
		[w / 2 - c, -h / 2 + c, -90.0], [w / 2 - c, h / 2 - c, 0.0],
		[-w / 2 + c, h / 2 - c, 90.0], [-w / 2 + c, -h / 2 + c, 180.0],
	]
	for k: Array in corners:
		for p in _arc_pts(c, k[2], k[2] + 90.0, 6):
			out.append(Vector2(k[0], k[1]) + p)
	return out


## Start an animation on a built rig. Returns the Tweens (kill them to stop).
## One Tween per track; loops by default. The rig must be inside the tree.
static func play(root: Node2D, ir: Dictionary, anim_name: String, loop: bool = true) -> Array[Tween]:
	var tweens: Array[Tween] = []
	var anim: Dictionary = ir["animations"].get(anim_name, {})
	if anim.is_empty():
		push_error("polygraphics: asset %s has no animation %s" % [ir["id"], anim_name])
		return tweens
	var duration: float = anim["duration"]
	for track: Dictionary in anim["tracks"]:
		for target in root.get_children():
			if not target.has_meta("pg_id") or String(target.get_meta("pg_id")) != String(track["part"]):
				continue
			var tw := target.create_tween()
			if loop:
				tw.set_loops()
			var keys: Array = track["keys"]
			var ease_name: String = track.get("ease", "sine")
			var first: Array = keys[0]
			_apply_prop(float(first[1]), target, String(track["prop"]))
			for i in range(1, keys.size()):
				var k0: Array = keys[i - 1]
				var k1: Array = keys[i]
				var seg := tw.tween_method(
					_apply_prop.bind(target, String(track["prop"])),
					float(k0[1]), float(k1[1]),
					(float(k1[0]) - float(k0[0])) * duration
				)
				match ease_name:
					"linear":
						seg.set_trans(Tween.TRANS_LINEAR)
					"backOut":
						seg.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
					_:
						seg.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
			tweens.append(tw)
	return tweens


static func _apply_prop(v: float, target: Node2D, prop: String) -> void:
	var sign: float = target.get_meta("pg_sign", 1.0)
	match prop:
		"x":
			target.position.x = (target.get_meta("pg_base_pos") as Vector2).x + v * sign
		"y":
			target.position.y = (target.get_meta("pg_base_pos") as Vector2).y + v
		"rot":
			target.rotation_degrees = float(target.get_meta("pg_base_rot")) + v * sign
		"scale":
			target.scale = (target.get_meta("pg_base_scale") as Vector2) * v
		"opacity":
			target.modulate.a = float(target.get_meta("pg_base_alpha")) * v


static func _vec(a: Array) -> Vector2:
	return Vector2(a[0], a[1])


static func _color(a: Array) -> Color:
	return Color(a[0], a[1], a[2], a[3])
