def hook():
    try:
        import wdb.ext
        wdb.ext.patch_werkzeug()
    except Exception:
        print("Can't hook wdb in werkzeug")
