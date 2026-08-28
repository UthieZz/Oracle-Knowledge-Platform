import re
from pathlib import Path
import subprocess
import hashlib

def run_packer():
    result = subprocess.run(["python", "split_markdown.py"], capture_output=True, text=True)
    return result.stdout, result.returncode

def get_dir_hash(directory):
    files = sorted(Path(directory).rglob("*"))
    hasher = hashlib.sha256()
    for f in files:
        if f.is_file():
            hasher.update(f.name.encode("utf-8"))
            hasher.update(f.read_bytes())
    return hasher.hexdigest()

def verify_data_integrity():
    print("Checking data integrity and reconstruction...")
    input_dir = Path("output")
    output_split_dir = Path("output_split")
    
    # Load all input files into memory
    original_docs = {}
    for f in sorted(input_dir.rglob("*.md")):
        rel_path = str(f.relative_to(input_dir))
        original_docs[rel_path] = f.read_bytes()
        
    # Reconstruct from packed outputs
    reconstructed_chunks = {}
    
    # We parse the output files in order
    for f in sorted(output_split_dir.glob("OKC_Knowledge_*.md")):
        content = f.read_bytes()
        
        # Every unit begins with b"<!-- SRC: "
        chunks = []
        idx = 0
        while True:
            start_idx = content.find(b"<!-- SRC: ", idx)
            if start_idx == -1:
                break
            # Find the next occurrence to determine the end
            next_idx = content.find(b"<!-- SRC: ", start_idx + 1)
            if next_idx == -1:
                chunk_data = content[start_idx:]
            else:
                chunk_data = content[start_idx:next_idx]
                # Strip trailing separator b"\n\n" from the chunk if present
                if chunk_data.endswith(b"\n\n"):
                    chunk_data = chunk_data[:-2]
            chunks.append(chunk_data)
            if next_idx == -1:
                break
            idx = next_idx
        
        for chunk in chunks:
            if not chunk:
                continue
            # Parse the provenance header
            # Format: <!-- SRC: path -->\n or <!-- SRC: path [Chunk num] -->\n
            match = re.match(br"^<!-- SRC: (.*?) -->\n", chunk)
            if not match:
                print(f"Error: Chunk does not start with expected header in {f.name}: {chunk[:100]}")
                return False
                
            header_full = match.group(0)
            src_info = match.group(1).decode("utf-8")
            
            # Check for chunk indicator
            chunk_match = re.match(r"^(.*?) \[Chunk (\d+)\]$", src_info)
            if chunk_match:
                rel_path = chunk_match.group(1)
                chunk_num = int(chunk_match.group(2))
            else:
                rel_path = src_info
                chunk_num = 1
                
            payload = chunk[len(header_full):]
            
            if rel_path not in reconstructed_chunks:
                reconstructed_chunks[rel_path] = []
            reconstructed_chunks[rel_path].append((chunk_num, payload))
            
    # Verify each reconstructed document matches the original exactly
    if len(original_docs) != len(reconstructed_chunks):
        print(f"Mismatch in file count! Original: {len(original_docs)}, Reconstructed: {len(reconstructed_chunks)}")
        return False
        
    for rel_path, chunks_list in reconstructed_chunks.items():
        if rel_path not in original_docs:
            print(f"Reconstructed file {rel_path} not found in original docs!")
            return False
            
        # Ensure chunks are ordered by chunk_num
        chunks_list.sort(key=lambda x: x[0])
        
        # Verify chunk numbers are sequential from 1
        expected_num = 1
        for num, _ in chunks_list:
            if num != expected_num:
                print(f"Missing chunk or gap in sequence for {rel_path}: got chunk {num}, expected {expected_num}")
                return False
            expected_num += 1
            
        # Reconstruct full body
        reconstructed_body = b"".join(payload for _, payload in chunks_list)
        original_body = original_docs[rel_path]
        
        if reconstructed_body != original_body:
            print(f"Byte mismatch in reconstructed document {rel_path}!")
            print(f"Original len: {len(original_body)}, Reconstructed len: {len(reconstructed_body)}")
            return False
            
    print("✅ INTEGRITY CHECK PASSED: Reconstructed documents match original files byte-for-byte!")
    return True

def main():
    print("Step 1: Running packer first time...")
    out1, code1 = run_packer()
    if code1 != 0:
        print("Packer failed on run 1!")
        print(out1)
        return
    hash1 = get_dir_hash("output_split")
    
    print("Step 2: Running packer second time to check determinism...")
    out2, code2 = run_packer()
    if code2 != 0:
        print("Packer failed on run 2!")
        return
    hash2 = get_dir_hash("output_split")
    
    if hash1 == hash2:
        print("✅ DETERMINISM CHECK PASSED: Both runs generated identical outputs.")
    else:
        print("❌ DETERMINISM CHECK FAILED!")
        print(f"Hash 1: {hash1}")
        print(f"Hash 2: {hash2}")
        return
        
    integrity_ok = verify_data_integrity()
    if integrity_ok:
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("\n❌ INTEGRITY TESTS FAILED!")

if __name__ == "__main__":
    main()
