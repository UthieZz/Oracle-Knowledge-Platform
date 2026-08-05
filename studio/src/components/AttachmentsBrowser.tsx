import React from 'react';
import GenericBrowser from './GenericBrowser';

const AttachmentsBrowser = () => {
  return (
    <GenericBrowser 
      title="Attachments" 
      endpoint="attachments" 
      columns={[
        { key: 'name', label: 'File Name' },
        { key: 'platform', label: 'Platform' },
        { key: 'conversation_title', label: 'Conversation' }
      ]} 
    />
  );
};

export default AttachmentsBrowser;
