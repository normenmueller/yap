"""Shared PDF destinations for the published, nested HTML views."""

from urllib.parse import quote

from .documents import pdf_target


def activity_pdf(node, anchor=""):
    """Link an activity or one of its sections to its canonical PDF target."""
    target = node["id"] + ("--" + anchor if anchor else "")
    return "../../acc/pdf/Activity - Details.pdf#nameddest=" + quote(pdf_target(target), safe="-_")


def objective_pdf(goal):
    """Link an Objective to its canonical PDF target."""
    return "../../acc/pdf/Performance - mPM.pdf#nameddest=" + quote(pdf_target(goal["id"]), safe="-_")
