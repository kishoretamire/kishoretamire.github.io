import { FiSearch } from 'react-icons/fi';

// In your search bar component
<button 
  className="search-button" 
  onClick={handleSearch}
  disabled={isLoading}
  type="button"
  aria-label="Search"
>
  <span className="button-content">
    <FiSearch className="search-icon" />
    <span className="button-text">
      {isLoading ? 'Searching...' : 'Search'}
    </span>
  </span>
</button> 