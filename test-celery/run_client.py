from tasks import add, sleep_task, check_file_exists, run_fake_gnina_job

job_payload = {
    "job_id": "batch_1__pocket1",
    "receptor_pdbqt_path": r"C:\Users\PC\OneDrive\Bureau\IA DRUG DISCOVERY\test_data\receptor.pdbqt",
    "ligand_sdf_path": r"C:\Users\PC\OneDrive\Bureau\IA DRUG DISCOVERY\test_data\ligands_clean_batch_1.sdf",
    "pocket_id": "pocket1",
    "center_x": 5.2422,
    "center_y": 11.3665,
    "center_z": 28.3128,
    "box_size": 20.0,
    "output_sdf_path": r"C:\Users\PC\OneDrive\Bureau\IA DRUG DISCOVERY\outputs\docked_batch_1_pocket1.sdf",
    "exhaustiveness": 20,
    "seed": 0,
}
filepath = "/home/ubuntu/drug-celery-test/data/test.txt"

result = check_file_exists.delay(filepath)

print("Task ID:", result.id)
print("Task sent. Waiting for result...")
print("Result:", result.get(timeout=10))