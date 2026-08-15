# Headless smoke test for the Godot adapter.
# Run: godot --headless -s scripts/test_godot_adapter.gd   (from the PolyGraphics root)
extends SceneTree

var failures := 0
var rig: Node2D
var imp: Dictionary
var base_body_y := 0.0
var elapsed := 0.0
var sampled := false

func check(name: String, cond: bool, detail: String = "") -> void:
	print(("✓ " if cond else "✖ ") + name + ("" if cond or detail == "" else " — " + detail))
	if not cond:
		failures += 1

## Colour of the `bulb` polygon inside the rig's `organ` node, whatever depth it sits at.
func _organ_bulb(rig: Node2D) -> Variant:
	for child in rig.get_children():
		if not child.has_meta("pg_id") or String(child.get_meta("pg_id")) != "organ":
			continue
		for grandchild in child.get_children():
			if grandchild.name != "bulb":
				continue
			for leaf in grandchild.get_children():
				if leaf is Polygon2D:
					return (leaf as Polygon2D).color
	return null

func _root_dir() -> String:
	# script lives in <root>/scripts/
	return (get_script() as Script).resource_path.get_base_dir().path_join("..")

func _init() -> void:
	var PG := load(_root_dir().path_join("adapters/godot/polygraphics.gd"))

	imp = PG.load_ir(_root_dir().path_join("out/compiled/enemy-imp.json"))
	check("load_ir reads IR", not imp.is_empty())

	rig = PG.build(imp)
	get_root().add_child(rig)
	check("build makes one Node2D per IR node (9)", rig.get_child_count() == 9, str(rig.get_child_count()))

	var eyes: Array[Node2D] = []
	var body: Node2D = null
	for c in rig.get_children():
		if String(c.get_meta("pg_id")) == "eye": eyes.append(c)
		if String(c.get_meta("pg_id")) == "body": body = c
	check("mirrored eye pair exists", eyes.size() == 2)
	check("eyes symmetric", eyes.size() == 2 and is_equal_approx(eyes[0].position.x, -eyes[1].position.x))
	check("mirrored eye has sign -1", eyes.size() == 2 and float(eyes[1].get_meta("pg_sign")) == -1.0)

	var poly: Polygon2D = null
	for c in body.get_children():
		if c is Polygon2D: poly = c
	check("body has a Polygon2D disc", poly != null and poly.polygon.size() == 48, str(poly.polygon.size() if poly else 0))
	check("body color resolved from token", poly != null and poly.color.is_equal_approx(Color(0.8392, 0.2157, 0.3373, 1.0)), str(poly.color if poly else null))

	var elite: Node2D = PG.build(imp, "elite")
	check("elite variant has third_eye (10 nodes)", elite.get_child_count() == 10, str(elite.get_child_count()))
	check("elite root scaled 1.25", is_equal_approx(elite.scale.x, 1.25))
	elite.free()

	var chest: Dictionary = PG.load_ir(_root_dir().path_join("out/compiled/pickup-chest.json"))
	var chest_rig: Node2D = PG.build(chest, "cursed")
	check("cursed chest builds", chest_rig.get_child_count() > 0)
	chest_rig.free()

	base_body_y = body.position.y
	# --- the premise mechanism: one shared organ document, two states, across engines.
	# ss.enemy.imp uses ss.lib.organ lit; ss.char.dot uses the same doc with variant "dead".
	var ss_imp: Dictionary = PG.load_ir(_root_dir().path_join("out/compiled/ss-enemy-imp.json"))
	var ss_dot: Dictionary = PG.load_ir(_root_dir().path_join("out/compiled/ss-char-dot.json"))
	var ss_imp_rig: Node2D = PG.build(ss_imp)
	var ss_dot_rig: Node2D = PG.build(ss_dot)
	var lit_v: Variant = _organ_bulb(ss_imp_rig)
	var dead_v: Variant = _organ_bulb(ss_dot_rig)
	ss_imp_rig.free()
	ss_dot_rig.free()
	check("both rigs expose an organ bulb", lit_v != null and dead_v != null)
	var lit: Color = lit_v if lit_v != null else Color.BLACK
	var dead: Color = dead_v if dead_v != null else Color.BLACK
	check("enemy organ resolves lit (pheromone magenta)",
		lit.r > 0.8 and lit.b > 0.7 and lit.g < 0.6, str(lit))
	check("player organ resolves dead (cold and dark)",
		dead.r < 0.35 and dead.g < 0.35 and dead.b < 0.35, str(dead))
	check("use-variant actually diverges across engines", not lit.is_equal_approx(dead))

	# 5 tracks, but eye + horn are mirrored pairs → 7 target nodes → 7 tweens
	var tweens: Array[Tween] = PG.play(rig, imp, "idle")
	check("play tweens every target node (5 tracks → 7 tweens)", tweens.size() == 7, str(tweens.size()))
	# _process pumps frames; we sample mid-cycle then quit

func _process(delta: float) -> bool:
	elapsed += delta
	if elapsed >= 0.5 and elapsed <= 0.62 and not sampled:
		sampled = true
		var body: Node2D = null
		for c in rig.get_children():
			if String(c.get_meta("pg_id")) == "body": body = c
		check("idle tween moves body up mid-cycle", body.position.y < base_body_y - 0.5,
			"y %.2f base %.2f" % [body.position.y, base_body_y])
	if elapsed > 0.7:
		print("FAILED: %d" % failures if failures else "ALL PASS")
		rig.queue_free()
		quit(1 if failures else 0)
	return false
