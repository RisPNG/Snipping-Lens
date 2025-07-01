from flask import Blueprint, render_template, request, jsonify

bp = Blueprint("main", __name__, template_folder="templates")


def make_chart(title):
    import json

    import plotly.graph_objects as go
    import plotly

    layout = go.Layout(title=title)

    data = go.Scatter(
        x=[1, 2, 3, 4],
        y=[10, 11, 12, 13],
        mode="markers",
        marker=dict(size=[40, 60, 80, 100], color=[0, 1, 2, 3]),
    )

    fig = go.Figure(data=data)
    fig = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    layout = json.dumps(layout, cls=plotly.utils.PlotlyJSONEncoder)
    return fig, layout


@bp.route("/", methods=["GET", "POST"])
def route():
    message = ""
    fig, layout = make_chart(title="Test title")
    return render_template("plotly-chart.html", fig=fig, layout=layout)

