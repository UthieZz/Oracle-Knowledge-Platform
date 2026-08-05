import React from 'react';
import GenericBrowser from './GenericBrowser';

const EntitiesBrowser = () => {
  return (
    <GenericBrowser 
      title="Entities" 
      endpoint="entities" 
      columns={[
        { key: 'value', label: 'Entity' },
        { key: 'type', label: 'Type' },
        { key: 'count', label: 'Mentions' }
      ]} 
    />
  );
};

export default EntitiesBrowser;
