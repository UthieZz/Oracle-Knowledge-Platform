import React from 'react';
import GenericBrowser from './GenericBrowser';

const KnowledgeObjectsBrowser = () => {
  return (
    <GenericBrowser 
      title="Knowledge Objects" 
      endpoint="knowledge-objects" 
      columns={[
        { key: 'title', label: 'Title' },
        { key: 'platform', label: 'Platform' }
      ]} 
    />
  );
};

export default KnowledgeObjectsBrowser;
