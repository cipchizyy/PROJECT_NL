# Tambahkan route ini ke customer.py

@customer_bp.route("/reservations/<string:reservation_id>/cancel", methods=["POST"])
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    # Pastikan hanya milik customer yang login
    if reservation.customer_id != current_user.id:
        flash("Tidak diizinkan membatalkan reservasi ini.", "danger")
        return redirect(url_for("customer.view_reservation"))

    if reservation.status != "pending":
        flash("Hanya reservasi dengan status pending yang bisa dibatalkan.", "warning")
        return redirect(url_for("customer.view_reservation"))

    reservation.status = "cancelled"
    db.session.commit()
    flash("Reservasi berhasil dibatalkan.", "success")
    return redirect(url_for("customer.view_reservation"))