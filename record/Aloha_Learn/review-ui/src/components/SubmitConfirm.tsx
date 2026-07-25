interface Props {
  accepted: number;
  edited: number;
  skipped: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SubmitConfirm({ accepted, edited, skipped, onConfirm, onCancel }: Props) {
  return (
    <div className="modal-backdrop" role="dialog" aria-label="Confirm submit">
      <div className="modal">
        <h2>确认提交</h2>
        <ul>
          <li>{`accept: ${accepted}`}</li>
          <li>{`edit: ${edited}`}</li>
          <li>{`skip: ${skipped}`}</li>
        </ul>
        <div className="modal-actions">
          <button onClick={onCancel} className="btn">再看看</button>
          <button onClick={onConfirm} className="btn btn-primary">确认提交</button>
        </div>
      </div>
    </div>
  );
}