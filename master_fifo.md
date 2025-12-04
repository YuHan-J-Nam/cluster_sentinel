# Commands written into `master_in` (FIFO)

These are the commands that were "echoed" into the `master_in` named pipe during the verification test:

```bash
echo "exec 0 utils/dummy_task.py"
echo "stop 0"
echo "end 0"
```
