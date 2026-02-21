from cortex import CortexClient, DistanceMetric

with CortexClient("100.100.165.29:50051") as client:
    # Health check
    version, uptime = client.health_check()
    print(f"Connected to {version}")

    # Create collection
    client.create_collection(
        name="products",
        dimension=128,
        distance_metric=DistanceMetric.COSINE,
    )

    # Insert vectors
    client.upsert("products", id=0, vector=[0.1]*128, payload={"name": "Product A"})

    # Batch insert
    client.batch_upsert(
        "products",
        ids=[1, 2, 3],
        vectors=[[0.2]*128, [0.3]*128, [0.4]*128],
        payloads=[{"name": f"Product {i}"} for i in [1, 2, 3]],
    )

    # Search
    results = client.search("products", query=[0.1]*128, top_k=5)
    for r in results:
        print(f"ID: {r.id}, Score: {r.score}")

    # Cleanup
    client.delete_collection("products")