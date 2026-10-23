        items.append({"id":r["id"],"sender":r["sender"],"sender_email":r["sender_email"],
            "mine":r["sender_uid"]==session["uid"],"body":r["body"],
            "image":url_for("uploaded_file",filename=r["image_name"]) if r["image_name"] else None,
            "time":time.strftime("%H:%M",time.localtime(r["created_at"]))})
    return jsonify(messages=items)

@app.post("/api/messages")
@api_login_required
def send_message():
    if not private_allowed():
        return private_forbidden()
    peer = request.form.get("to", "").strip()
    body = request.form.get("message", "").strip()
    image = request.files.get("image")
    if len(body) > 4000:
        return jsonify(error="Messages must be under 4,000 characters."), 400
    image_name = save_image(image)
    if image_name is False:
        return jsonify(error="Use PNG, JPG, GIF or WEBP images."), 400
    if not body and not image_name:
        return jsonify(error="Write a message or choose an image."), 400
    with db() as conn:
        other = conn.execute("SELECT uid,email FROM users WHERE username=?", (peer,)).fetchone()
        if not other or other["email"].strip().lower() not in PRIVATE_EMAILS or other["uid"] == session["uid"]:
            if image_name: (UPLOAD_DIR / image_name).unlink(missing_ok=True)
            return jsonify(error="Private messages can only be sent to the other authorized account."), 403
        conn.execute("INSERT INTO messages(sender_uid,recipient_uid,body,image_name,created_at) VALUES(?,?,?,?,?)",
                     (session["uid"],other["uid"],body or None,image_name,int(time.time())))
    return jsonify(ok=True)

def save_image(image):
    if not image or not image.filename:
        return None
    ext = image.filename.rsplit(".",1)[-1].lower() if "." in image.filename else ""
    if ext not in ALLOWED:
        return False
    safe = secure_filename(image.filename) or "image"
    name = f"{secrets.token_hex(16)}_{safe}"
    image.save(UPLOAD_DIR / name)
    return name

@app.get("/api/community/messages")
@api_login_required
def get_community_messages():
    with db() as conn:
        rows = conn.execute("""SELECT c.id,c.sender_uid,c.sender_username,c.body,c.image_name,c.created_at,u.email AS sender_email
            FROM community_messages c LEFT JOIN users u ON u.uid=c.sender_uid
            ORDER BY c.id DESC LIMIT 200""").fetchall()
    items=[]
    for r in reversed(rows):
        email=(r["sender_email"] or "").strip().lower()
        items.append({"id":r["id"],"sender":r["sender_username"],"sender_username":r["sender_username"],
            "sender_email":email,"special":email in SPECIAL_EMAILS,"sender_uid":r["sender_uid"],
            "mine":r["sender_uid"]==session["uid"],"body":r["body"],
            "image":url_for("uploaded_file",filename=r["image_name"]) if r["image_name"] else None,
            "time":time.strftime("%H:%M",time.localtime(r["created_at"]))})
    return jsonify(messages=items)

@app.post("/api/community/messages")
@api_login_required
def send_community_message():
    body=request.form.get("message","").strip()
    image= request.files.get("image")
    if len(body)>4000:
        return jsonify(error="Messages must be under 4,000 characters."),400
    image_name=save_image(image)
    if image_name is False:
        return jsonify(error="Use PNG, JPG, GIF or WEBP images."),400
    if not body and not image_name:
        return jsonify(error="Write a message or choose an image."),400
    with db() as conn:
        conn.execute("""INSERT INTO community_messages(sender_uid,sender_username,body,image_name,created_at)
            VALUES(?,?,?,?,?)""",(session["uid"],session["username"],body or None,image_name,int(time.time())))
    return jsonify(ok=True)

@app.delete("/api/community/messages/<int:message_id>")
@api_login_required
def delete_community_message(message_id):
    with db() as conn:
        row=conn.execute("SELECT sender_uid,image_name FROM community_messages WHERE id=?",(message_id,)).fetchone()
        if not row:
            return jsonify(error="Message not found."),404
        if row["sender_uid"] != session["uid"]:
            return jsonify(error="You can only delete your own messages."),403
        conn.execute("DELETE FROM community_messages WHERE id=?",(message_id,))
    if row["image_name"]:
        (UPLOAD_DIR / row["image_name"]).unlink(missing_ok=True)
    return jsonify(ok=True)

@app.delete("/api/messages/<int:message_id>")
@api_login_required
def delete_private_message(message_id):
    if not private_allowed():
        return private_forbidden()
    with db() as conn:
        row=conn.execute("SELECT sender_uid,image_name FROM messages WHERE id=?",(message_id,)).fetchone()
        if not row:
            return jsonify(error="Message not found."),404
        if row["sender_uid"] != session["uid"]:
            return jsonify(error="You can only delete your own messages."),403
        conn.execute("DELETE FROM messages WHERE id=?",(message_id,))
    if row["image_name"]:
        (UPLOAD_DIR / row["image_name"]).unlink(missing_ok=True)
    return jsonify(ok=True)

@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    if "/" in filename or "\\" in filename:
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename, max_age=3600)

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Image is too large. Maximum size is 10 MB."),413

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
