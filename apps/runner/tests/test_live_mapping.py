from runner.live import map_pointer_to_page


def test_pointer_mapping():
    x, y = map_pointer_to_page(
        canvas_x=50, canvas_y=25, canvas_w=100, canvas_h=50, page_w=800, page_h=600
    )
    assert abs(x - 400) < 0.01 and abs(y - 300) < 0.01
