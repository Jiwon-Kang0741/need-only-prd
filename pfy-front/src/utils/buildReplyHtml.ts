import { formatUtcDate } from '@/utils/formatDate';

export const buildReplyHtml = ({
  inquiryContent = '',
  replyName = '',
  replyDate = '',
  replyContent = '',
  inquiryName = '',
  inquiryDate = '',
}: {
  inquiryContent: string;
  inquiryName: string;
  inquiryDate: string;
  replyName: string;
  replyDate: string;
  replyContent: string;
}) => {
  const replyBlock = `
    <hr />
    <div>
      <p><b>From:</b> ${replyName || ''}</p>
      <p><b>Sent:</b> ${formatUtcDate(replyDate) || ''}</p>
      <p><b>Content:</b></p>
      <div>
        ${replyContent || ''}
      </div>
    </div>
    <hr />
        <div>
      <p><b>From:</b> ${inquiryName || ''}</p>
      <p><b>Sent:</b> ${formatUtcDate(inquiryDate) || ''}</p>
      <p><b>Content:</b></p>
      <div>
        ${inquiryContent || ''}
      </div>
    </div>
  `;

  return replyBlock;
};
