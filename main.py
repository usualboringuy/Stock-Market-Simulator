from jugaad_data.nse import NSELive

client = NSELive()
data = client.live_fno()
print(data.keys())
print(data.get("data", [])[:3])  # sample first 5 entries
